#!/usr/bin/env python
"""Lightweight health check utility for the ChatAI + DataLab stack."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

from datalab.diagnostics import append_diagnostic_record
from datalab.lab_paths import data_path, describe_environment, get_lab_root

DEFAULT_STATUS_URL = "http://localhost:8000/api/control/status"


def check_database(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(path)}
    if not path.exists():
        payload["status"] = "missing"
        return payload

    try:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("SELECT COUNT(1) FROM interactions").fetchone()
            payload["records"] = int(row[0]) if row else 0
            payload["status"] = "ok"
        finally:
            conn.close()
    except sqlite3.Error as exc:  # pragma: no cover - defensive guard
        payload["status"] = "error"
        payload["error"] = str(exc)
    payload["size_bytes"] = path.stat().st_size if path.exists() else 0
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
    parser = argparse.ArgumentParser(description="ChatAI Control health probe")
    parser.add_argument("--status-url", default=DEFAULT_STATUS_URL, help="Control status endpoint to query")
    parser.add_argument(
        "--db-path",
        default=str(data_path("interactions.db")),
        help="Path to the shared interactions SQLite database",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve()
    checks = {
        "database": check_database(db_path),
        "control_status": check_status_endpoint(args.status_url),
        "environment": check_environment(),
    }
    overall = aggregate_status(checks)

    append_diagnostic_record(
        category="healthcheck",
        message="Control health probe",
        data={"overall": overall, **checks},
    )

    payload = {"overall": overall, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_summary(overall, checks))

    if overall == "fail":
        sys.exit(2)
    if overall == "degraded":
        sys.exit(1)


if __name__ == "__main__":
    os.environ.setdefault("LAB_ROOT", str(get_lab_root()))
    main()
