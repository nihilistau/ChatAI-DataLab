from __future__ import annotations

import json
from pathlib import Path

from playground.backend.app.services.search_telemetry import get_search_telemetry_summary
from kitchen.scripts import search_telemetry as telemetry


def _write_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


def _build_sample_entries() -> list[dict]:
    payloads: list[dict] = []
    for idx in range(3):
        payloads.append(
            {
                "timestamp": f"2025-11-1{idx}T12:00:00Z",
                "pattern": "TODO",
                "preset": "todo-scan",
                "filesScanned": 12,
                "matches": 4,
                "durationMs": 120,
            }
        )
    for idx in range(3):
        payloads.append(
            {
                "timestamp": f"2025-11-2{idx}T12:00:00Z",
                "pattern": "TODO",
                "preset": "todo-scan",
                "filesScanned": 12,
                "matches": 0,
                "durationMs": 210,
            }
        )
    for idx in range(4):
        payloads.append(
            {
                "timestamp": f"2025-11-0{idx + 1}T06:30:00Z",
                "pattern": "FIXME",
                "preset": "fixme-scan",
                "filesScanned": 8,
                "matches": 1,
                "durationMs": 80,
            }
        )
    return payloads


def test_summary_includes_preset_drift(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "history.jsonl"
    db_path = tmp_path / "telemetry.db"
    _write_entries(log_path, _build_sample_entries())

    telemetry.ingest_search_history(log_path, db_path)

    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps({"preset_tags": {"todo-scan": ["docs"], "fixme-scan": ["backend"]}}))

    summary = get_search_telemetry_summary(
        db_path=db_path,
        preset_drift_lookback=4,
        preset_tags_path=tags_path,
    )

    assert summary["total_runs"] == 10
    assert summary["preset_drift"], "Preset drift payload should not be empty"

    todo_entry = next(item for item in summary["preset_drift"] if item["preset"] == "todo-scan")
    assert todo_entry["status"] == "regressing"
    assert todo_entry["tags"] == ["docs"]
    assert todo_entry["recent_runs"] == 4

    fixme_entry = next(item for item in summary["preset_drift"] if item["preset"] == "fixme-scan")
    assert fixme_entry["status"] == "stable"
    assert fixme_entry["match_rate_recent"] == fixme_entry["match_rate_lifetime"]