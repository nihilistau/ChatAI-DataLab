"""Structured diagnostics helpers shared by notebooks, scripts, and Kitchen hooks."""
# @tag: kitchen,diagnostics

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .lab_paths import data_path, describe_environment, ensure_directory, lab_path, logs_path

DEFAULT_DIAGNOSTICS_LOG = logs_path("lab-diagnostics.jsonl")
DEFAULT_SNAPSHOT_PATH = lab_path("datalab", "_papermill", "control_center_snapshot.json")
DEFAULT_METADATA_PATH = lab_path("datalab", "_papermill", "run_metadata.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_diagnostic_record(
    *,
    category: str,
    message: str,
    data: dict | None = None,
    log_path: Path | None = None,
) -> Path:
    """Append a single structured record to the diagnostics log."""

    record = {
        "timestamp": _now(),
        "category": category,
        "message": message,
        "data": data or {},
    }
    path = ensure_directory(log_path or DEFAULT_DIAGNOSTICS_LOG)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def iter_diagnostic_records(limit: int = 50, log_path: Path | None = None) -> list[dict[str, Any]]:
    """Return the most recent diagnostics entries (best-effort)."""

    path = log_path or DEFAULT_DIAGNOSTICS_LOG
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def write_snapshot(payload: dict[str, Any], snapshot_path: Path | None = None) -> Path:
    """Persist the latest Control Center snapshot to disk."""

    path = ensure_directory(snapshot_path or DEFAULT_SNAPSHOT_PATH)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def record_run_metadata(
    *,
    parameters: dict | None = None,
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    """Persist run metadata (LAB_ROOT, DB path, etc.) alongside notebooks for traceability."""

    payload = describe_environment(parameters or {})
    payload["generated_at"] = _now()
    path = ensure_directory(snapshot_path or DEFAULT_METADATA_PATH)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def get_default_paths() -> dict[str, str]:
    """Expose canonical data/log paths for PowerShell diagnostics."""

    return {
        "logs": str(DEFAULT_DIAGNOSTICS_LOG),
        "snapshot": str(DEFAULT_SNAPSHOT_PATH),
        "metadata": str(DEFAULT_METADATA_PATH),
        "data": str(data_path()),
    }


__all__ = [
    "DEFAULT_DIAGNOSTICS_LOG",
    "DEFAULT_METADATA_PATH",
    "DEFAULT_SNAPSHOT_PATH",
    "append_diagnostic_record",
    "get_default_paths",
    "iter_diagnostic_records",
    "record_run_metadata",
    "write_snapshot",
]
