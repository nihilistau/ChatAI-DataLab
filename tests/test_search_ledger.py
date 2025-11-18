from __future__ import annotations

import json
from pathlib import Path

import pytest

from kitchen.telemetry import search_ledger

try:  # pragma: no cover - optional dependency
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - skip at runtime if dependency missing
    pq = None


@pytest.mark.skipif(pq is None, reason="pyarrow not installed")
def test_ingest_search_history_writes_parquet(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "history.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "timestamp": "2025-11-01T12:00:00Z",
            "pattern": "TODO",
            "preset": "todo-scan",
            "filesScanned": 12,
            "matches": 3,
            "durationMs": 90,
        },
        {
            "timestamp": "2025-11-02T12:05:00Z",
            "pattern": "FIXME",
            "preset": "fixme-scan",
            "filesScanned": 8,
            "matches": 0,
            "durationMs": 120,
        },
    ]
    with log_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")

    runs_parquet = tmp_path / "runs.parquet"
    daily_parquet = tmp_path / "daily.parquet"
    summary_path = tmp_path / "summary.json"

    summary = search_ledger.ingest_search_history(
        log_path,
        summary_path,
        runs_parquet_path=runs_parquet,
        daily_parquet_path=daily_parquet,
        emit_tail_log=False,
    )

    assert runs_parquet.exists()
    assert daily_parquet.exists()

    runs_table = pq.read_table(runs_parquet)
    assert runs_table.num_rows == len(summary.get("runs", []))

    daily_table = pq.read_table(daily_parquet)
    assert daily_table.num_rows == len(summary.get("daily_metrics", []))
