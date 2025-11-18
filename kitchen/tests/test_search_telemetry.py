from __future__ import annotations

"""Unit tests for kitchen.scripts.search_telemetry."""

# @tag:kitchen,tests,telemetry

import json
from pathlib import Path

import pandas as pd

from kitchen.scripts import search_telemetry as telemetry


SAMPLE_ENTRIES = [
	{
		"timestamp": "2025-11-15T12:00:00Z",
		"pattern": "TODO",
		"preset": "todo-scan",
		"regex": False,
		"caseSensitive": False,
		"root": "./",
		"recursive": True,
		"includeFiles": ["*.py"],
		"excludePatterns": ["node_modules"],
		"filesScanned": 5,
		"matches": 2,
		"durationMs": 150,
	},
	{
		"timestamp": "2025-11-16T08:30:00Z",
		"pattern": "FIXME",
		"preset": "todo-scan",
		"regex": False,
		"caseSensitive": False,
		"root": "./",
		"recursive": True,
		"includeFiles": ["*.ts"],
		"excludePatterns": ["storybook"],
		"filesScanned": 3,
		"matches": 0,
		"durationMs": 90,
	},
]


def _write_log(log_path: Path) -> None:
	log_path.parent.mkdir(parents=True, exist_ok=True)
	with log_path.open("w", encoding="utf-8") as handle:
		for entry in SAMPLE_ENTRIES:
			handle.write(json.dumps(entry) + "\n")


def test_ingest_creates_search_runs(tmp_path: Path) -> None:
	log_path = tmp_path / "logs" / "search-history.jsonl"
	db_path = tmp_path / "search.db"
	_write_log(log_path)

	stats = telemetry.ingest_search_history(log_path, db_path)

	assert stats.inserted == len(SAMPLE_ENTRIES)
	frame = telemetry.load_search_runs(db_path)
	assert isinstance(frame, pd.DataFrame)
	assert len(frame) == len(SAMPLE_ENTRIES)
	assert frame.iloc[0]["pattern"] in {"TODO", "FIXME"}


def test_ingest_is_idempotent(tmp_path: Path) -> None:
	log_path = tmp_path / "logs" / "search-history.jsonl"
	db_path = tmp_path / "search.db"
	_write_log(log_path)

	first_run = telemetry.ingest_search_history(log_path, db_path)
	second_run = telemetry.ingest_search_history(log_path, db_path)

	assert first_run.inserted == len(SAMPLE_ENTRIES)
	assert second_run.inserted == 0

	metrics_frame = telemetry.load_daily_metrics(db_path)
	assert set(metrics_frame["event_date"]) == {"2025-11-15", "2025-11-16"}
	assert metrics_frame.loc[metrics_frame["event_date"] == "2025-11-15", "runs_with_matches"].iloc[0] == 1


def test_compute_preset_drift_flags_regressions(tmp_path: Path) -> None:
	log_path = tmp_path / "logs" / "search-history.jsonl"
	db_path = tmp_path / "search.db"
	log_path.parent.mkdir(parents=True, exist_ok=True)

	entries: list[dict] = []
	# Older successful runs for todo-scan
	for idx in range(3):
		entries.append(
			{
				"timestamp": f"2025-11-0{idx + 1}T00:00:00Z",
				"pattern": "TODO",
				"preset": "todo-scan",
				"filesScanned": 10,
				"matches": 5,
				"durationMs": 120,
			}
		)
	# Recent failing runs for todo-scan
	for idx in range(3):
		entries.append(
			{
				"timestamp": f"2025-11-2{idx}T00:00:00Z",
				"pattern": "TODO",
				"preset": "todo-scan",
				"filesScanned": 10,
				"matches": 0,
				"durationMs": 200,
			}
		)
	# Stable preset for comparison
	for idx in range(4):
		entries.append(
			{
				"timestamp": f"2025-11-1{idx}T05:00:00Z",
				"pattern": "FIXME",
				"preset": "fixme-scan",
				"filesScanned": 8,
				"matches": 1,
				"durationMs": 80,
			}
		)

	with log_path.open("w", encoding="utf-8") as handle:
		for entry in entries:
			handle.write(json.dumps(entry) + "\n")

	telemetry.ingest_search_history(log_path, db_path)

	tags_path = tmp_path / "tags.json"
	tags_path.write_text(json.dumps({"preset_tags": {"todo-scan": ["docs"], "fixme-scan": "backend"}}))

	drift = telemetry.compute_preset_drift(db_path, lookback=4, preset_tags_path=tags_path)

	todo_entry = next(item for item in drift if item["preset"] == "todo-scan")
	assert todo_entry["status"] == "regressing"
	assert todo_entry["tags"] == ["docs"]
	assert todo_entry["recent_runs"] == 4
	assert todo_entry["match_rate_recent"] < todo_entry["match_rate_lifetime"]

	fixme_entry = next(item for item in drift if item["preset"] == "fixme-scan")
	assert fixme_entry["status"] == "stable"
