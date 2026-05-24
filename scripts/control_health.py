#!/usr/bin/env python
"""Lightweight health check utility for the Relay stack."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workshop.diagnostics import append_diagnostic_record
from workshop.lab_paths import data_path, describe_environment, get_lab_root
from relay.backend.app.config import get_settings
from relay.backend.app.services.data_store import data_store_context
from scripts.ops_telemetry import telemetry_span

DEFAULT_STATUS_URL = "http://localhost:8000/api/control/status"


def check_data_store() -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {"provider": settings.database_provider}

    sqlite_path: Path | None = None
    if settings.database_provider == "sqlite":
        sqlite_path = Path(settings.database_path).expanduser()
        payload["path"] = str(sqlite_path)
        payload["size_bytes"] = sqlite_path.stat().st_size if sqlite_path.exists() else 0
        if not sqlite_path.exists():
            payload["status"] = "missing"
            return payload

    try:
        with data_store_context() as store:
            count = store.count_interactions()
            payload["interaction_count"] = count
            latest = store.list_interactions(limit=3)
            payload["latest_interactions"] = [
                {
                    "id": item.id,
                    "model": item.model_name,
                    "prompt_preview": item.user_prompt_text[:80],
                    "created_at": item.created_at.isoformat(),
                }
                for item in latest
            ]
            payload["status"] = "ok"
    except Exception as exc:  # pragma: no cover - defensive guard
        payload["status"] = "error"
        payload["error"] = str(exc)

    return payload


def check_status_endpoint(url: str) -> dict[str, Any]:
    start = time.perf_counter()
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    result: dict[str, Any] = {"url": url}
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            latency_ms = (time.perf_counter() - start) * 1000
            body = response.read().decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {}
            result.update(
                {
                    "status": "ok",
                    "http_status": response.status,
                    "latency_ms": round(latency_ms, 2),
                    "service_count": len(payload.get("services", [])),
                }
            )
    except urllib.error.URLError as exc:
        result.update(
            {
                "status": "error",
                "error": str(exc.reason if hasattr(exc, "reason") else exc),
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        )
    except TimeoutError:
        result.update(
            {
                "status": "error",
                "error": "Timeout",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        )
    return result


def check_environment() -> dict[str, Any]:
    snapshot = describe_environment()
    env_root = snapshot.get("lab_root_env")
    detected_root = snapshot.get("lab_root")
    status = "ok" if env_root and env_root == detected_root else "degraded"
    return {"status": status, "lab_root": detected_root, "lab_root_env": env_root}


def aggregate_status(checks: Dict[str, dict[str, Any]]) -> str:
    if any(check.get("status") == "error" for check in checks.values()):
        return "fail"
    if any(check.get("status") != "ok" for check in checks.values()):
        return "degraded"
    return "ok"


def format_summary(overall: str, checks: Dict[str, dict[str, Any]]) -> str:
    lines = [f"Overall status: {overall.upper()}\n"]
    for name, payload in checks.items():
        headline = f"[{name}] {payload.get('status', 'unknown').upper()}"
        details = {k: v for k, v in payload.items() if k not in {"status"}}
        lines.append(headline)
        if details:
            lines.append(json.dumps(details, indent=2))
        lines.append("")
    return "\n".join(lines).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relay control health probe")
    parser.add_argument("--status-url", default=DEFAULT_STATUS_URL, help="Control status endpoint to query")
    parser.add_argument(
        "--db-path",
        default=str(data_path("interactions.db")),
        help="Path to the shared interactions SQLite database",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission for this probe")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="control-health", help="Tail log source label")
    parser.add_argument(
        "--release-log-kind",
        default="control_health",
        help="Kind label recorded in release log entries",
    )
    parser.add_argument(
        "--release-log-path",
        default=None,
        help="Optional override for the release log path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if "--db-path" in sys.argv:
        os.environ["DATABASE_PATH"] = str(Path(args.db_path).expanduser().resolve())
    overall_holder: dict[str, str | None] = {"status": None}
    checks: dict[str, dict[str, Any]] = {}
    payload: dict[str, Any] = {}

    release_entry = {
        "kind": "control_health",
        "action": "control_health",
        "status_url": args.status_url,
    }
    release_details = {
        "status_url": args.status_url,
        "db_path": args.db_path,
    }

    def _tail_message() -> str:
        overall_status = overall_holder["status"] or "pending"
        return f"control health · overall={overall_status}"

    with telemetry_span(
        "control-health",
        component="control_health",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary="Control health probe",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as span:
        checks = {
            "data_store": check_data_store(),
            "control_status": check_status_endpoint(args.status_url),
            "environment": check_environment(),
        }
        for name, result in checks.items():
            span.record_step(name, status=result.get("status", "unknown"), details=result)

        overall = aggregate_status(checks)
        overall_holder["status"] = overall
        span.record_step("aggregate", status="ok", details={"overall": overall})
        span.set_metadata(overall=overall, status_url=args.status_url)

        release_entry.update({"overall": overall, "checks": checks})

        append_diagnostic_record(
            category="healthcheck",
            message="Control health probe",
            data={"overall": overall, **checks},
        )

        payload = {"overall": overall, "checks": checks}

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_summary(overall_holder["status"] or "unknown", checks))

    if overall_holder["status"] == "fail":
        sys.exit(2)
    if overall_holder["status"] == "degraded":
        sys.exit(1)


if __name__ == "__main__":
    os.environ.setdefault("LAB_ROOT", str(get_lab_root()))
    main()
