from __future__ import annotations

"""Helpers for reading structured release log entries from disk."""
# @tag: backend,services,release-log

import hashlib
import json
from pathlib import Path
from typing import Any

from ..config import get_settings


def _stable_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return digest[:16]


def _infer_kind(payload: dict[str, Any]) -> str:
    if payload.get("kind"):
        return str(payload["kind"])
    if "tag" in payload or "release_dir" in payload:
        return "release_pipeline"
    return "workflow_harness"


def _load_entries_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(payload)
    return entries


def list_release_log_entries(limit: int) -> list[dict[str, Any]]:
    """Return the newest ``limit`` entries from data/logs/release.log."""

    settings = get_settings()
    path = settings.release_log_path
    entries = _load_entries_from_file(path)
    if not entries:
        return []

    selected = entries[-limit:]
    normalized: list[dict[str, Any]] = []
    for raw in reversed(selected):
        payload = dict(raw)
        payload["kind"] = _infer_kind(payload)
        payload["timeline"] = payload.get("timeline") or []
        payload.setdefault("options", raw.get("options"))
        payload.setdefault("release_mode", raw.get("release_mode"))
        payload.setdefault("timestamp", raw.get("timestamp"))
        payload.setdefault("action", raw.get("action"))
        payload.setdefault("status", raw.get("status"))
        payload.setdefault("source", raw.get("source"))
        payload.setdefault("duration_seconds", raw.get("duration_seconds"))
        payload.setdefault("summary", raw.get("summary"))
        payload.setdefault("details", raw.get("details"))
        payload.setdefault("metadata", raw.get("metadata"))
        payload.setdefault("error", raw.get("error"))
        payload.setdefault("reference", raw.get("reference"))
        payload["id"] = payload.get("id") or _stable_id(payload)
        normalized.append(payload)
    return normalized
