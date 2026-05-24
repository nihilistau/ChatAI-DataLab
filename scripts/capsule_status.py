#!/usr/bin/env python3
"""Relay capsule status + artifact hygiene CLI with telemetry."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_telemetry import telemetry_span
from workshop.scripts.capsule_snapshot import check_api, check_dependencies, check_notebook

DEFAULT_MANIFEST = ROOT / "configs" / "capsules" / "onboarding.json"
DEFAULT_SNAPSHOT = ROOT / "data" / "relay-onboarding-snapshot.json"
DEFAULT_LOG = ROOT / "logs" / "relay_status.jsonl"
DEFAULT_ARTIFACT_DIR = ROOT / "release_artifacts"

INTEGRITY_CMD = [sys.executable, str(ROOT / "scripts" / "project_integrity.py"), "status", "--json"]
BUGHUNT_CMD = [
    "pwsh",
    "-File",
    str(ROOT / "scripts" / "powershell" / "SearchToolkit.psm1"),
    "Search-LabRepo",
    "-Preset",
    "bug-hunt",
    "-Output",
    "json",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _fetch_integrity_status() -> dict[str, Any]:
    try:
        result = subprocess.run(
            INTEGRITY_CMD,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = result.stdout.strip() or "{}"
        return json.loads(payload)
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return {"error": str(exc)}


def _fetch_bughunt_status() -> dict[str, Any]:
    try:
        result = subprocess.run(
            BUGHUNT_CMD,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = result.stdout.strip() or "{}"
        return json.loads(payload)
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return {"error": str(exc)}


def get_relay_status(
    manifest_path: Path,
    snapshot_path: Path,
    artifact_dir: Path,
    log_path: Path | None,
) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    snapshot = _read_json(snapshot_path) if snapshot_path.exists() else None

    deps = manifest.get("environment", {}).get("dependencies", [])
    missing_deps = check_dependencies(deps) if deps else []
    notebooks = manifest.get("notebooks", [])
    notebook_health = {nb: check_notebook(nb) for nb in notebooks}
    api_url = manifest.get("environment", {}).get("api_url")
    api_health = check_api(api_url) if api_url else None
    integrity_status = _fetch_integrity_status()
    bughunt_status = _fetch_bughunt_status()

    status = {
        "relay": manifest.get("relay_name", "unknown"),
        "version": manifest.get("version"),
        "last_run": manifest.get("state", {}).get("last_run"),
        "user": manifest.get("state", {}).get("user"),
        "snapshot_exists": snapshot_path.exists(),
        "snapshot_created": snapshot.get("created") if snapshot else None,
        "notebooks": notebooks,
        "notebook_health": notebook_health,
        "missing_dependencies": missing_deps,
        "api_health": api_health,
        "artifact_folder": _relativize(artifact_dir),
        "artifact_retained": artifact_dir.exists(),
        "status_checked": datetime.now(timezone.utc).isoformat(),
        "integrity": integrity_status,
        "bughunt": bughunt_status,
    }

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(status))
            handle.write("\n")

    print(json.dumps(status, indent=2))
    return status


def cleanup_artifacts(artifact_dir: Path, retention_days: int) -> list[str]:
    now = time.time()
    cutoff = now - retention_days * 86400
    removed: list[str] = []
    if artifact_dir.exists():
        for item in artifact_dir.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink(missing_ok=True)
                removed.append(_relativize(item))
    return removed


def _classify_status(status: dict[str, Any]) -> str:
    if status.get("integrity", {}).get("error") or status.get("bughunt", {}).get("error"):
        return "failed"
    if status.get("missing_dependencies"):
        return "degraded"
    notebook_health = status.get("notebook_health", {})
    if any(not value for value in notebook_health.values()):
        return "degraded"
    if status.get("api_health") is False:
        return "degraded"
    return "ok"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Relay status reporter")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to relay manifest")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="Path to cached snapshot JSON")
    parser.add_argument("--log", default=str(DEFAULT_LOG), help="Optional JSONL log destination")
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR), help="Release artifacts directory")
    parser.add_argument("--retention-days", type=int, default=30, help="Artifact retention window (days)")
    parser.add_argument("--periodic", action="store_true", help="Continuously run the probe")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between periodic probes")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="capsule-status", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="capsule_status", help="Release log kind label")
    parser.add_argument("--release-log-path", default=None, help="Optional release log override path")
    return parser


def run_capsule_status(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.manifest).expanduser().resolve()
    snapshot_path = Path(args.snapshot).expanduser().resolve()
    artifact_dir = Path(args.artifact_dir).expanduser().resolve()
    log_path = Path(args.log).expanduser().resolve() if args.log else None

    status_holder: dict[str, Any] = {}

    def _tail_message() -> str:
        if "status" not in status_holder:
            return f"capsule status pending · manifest={_relativize(manifest_path)}"
        data = status_holder["status"]
        return f"capsule status · relay={data.get('relay', 'unknown')} · status={data.get('overall', 'ok')}"

    release_entry = {
        "kind": "capsule_status",
        "action": "capsule_status",
        "manifest": _relativize(manifest_path),
        "snapshot": _relativize(snapshot_path),
    }
    release_details = {
        "manifest": _relativize(manifest_path),
        "snapshot": _relativize(snapshot_path),
        "artifact_dir": _relativize(artifact_dir),
        "retention_days": args.retention_days,
        "periodic": args.periodic,
        "interval": args.interval,
        "log_path": _relativize(log_path) if log_path else None,
    }

    with telemetry_span(
        "capsule-status",
        component="capsule_status",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary="Capsule status probe",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as recorder:
        status = get_relay_status(manifest_path, snapshot_path, artifact_dir, log_path)
        status["overall"] = _classify_status(status)
        status_holder["status"] = status

        recorder.record_step(
            "relay_status",
            status=status["overall"],
            details={
                "relay": status.get("relay"),
                "version": status.get("version"),
                "missing_dependencies": len(status.get("missing_dependencies", [])),
                "notebook_errors": sum(1 for ok in status.get("notebook_health", {}).values() if not ok),
                "api_health": status.get("api_health"),
            },
        )

        removed = cleanup_artifacts(artifact_dir, args.retention_days)
        if removed:
            recorder.record_step("artifact_cleanup", status="ok", details={"removed": removed})
            print(f"Removed old artifacts: {removed}")

        recorder.set_metadata(
            relay=status.get("relay"),
            version=status.get("version"),
            overall=status["overall"],
            manifest=_relativize(manifest_path),
        )
        release_entry.update(
            {
                "relay": status.get("relay"),
                "version": status.get("version"),
                "overall": status["overall"],
                "removed_artifacts": len(removed),
            }
        )

        return status


def periodic_status(args: argparse.Namespace) -> None:
    while True:
        run_capsule_status(args)
        time.sleep(max(1, args.interval))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.periodic:
        periodic_status(args)
        return 0
    run_capsule_status(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
