from __future__ import annotations

"""Unit tests for kitchen.scripts.metrics helpers."""

# @tag:kitchen,tests,analytics

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from kitchen.scripts import metrics


def test_load_interactions_reads_latest_first(tmp_path: Path) -> None:
	db_path = tmp_path / "interactions.db"
	conn = sqlite3.connect(db_path)
	try:
		conn.execute(
			"""
			CREATE TABLE interactions (
				id TEXT PRIMARY KEY,
				user_prompt_text TEXT,
				typing_metadata_json TEXT,
				created_at TEXT
			)
			"""
		)
		conn.executemany(
			"INSERT INTO interactions VALUES (?, ?, ?, ?)",
			[
				("1", "first", "{}", "2024-01-01T00:00:00Z"),
				("2", "second", "{}", "2024-01-02T00:00:00Z"),
			],
		)
		conn.commit()
	finally:
		conn.close()

	frame = metrics.load_interactions(db_path)

	assert list(frame["id"]) == ["2", "1"], "Rows should be sorted by created_at DESC"


def test_load_interactions_uses_datastore_when_no_path(monkeypatch: pytest.MonkeyPatch) -> None:
	record = SimpleNamespace(
		id="abc",
		user_prompt_text="hello",
		typing_metadata_json={"keystroke_events": []},
		ai_response_text="hi",
		model_name="echo",
		latency_ms=42,
		created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
	)

	class DummyStore:
		def __init__(self) -> None:
			self.list_calls: list[int] = []

		def count_interactions(self) -> int:
			return 1

		def list_interactions(self, limit: int):
			self.list_calls.append(limit)
			return [record]

	@contextmanager
	def fake_context():
		yield DummyStore()

	monkeypatch.setattr(metrics, "data_store_context", fake_context)

	frame = metrics.load_interactions()

	assert list(frame["id"]) == ["abc"]
	assert frame.iloc[0]["typing_metadata_json"] == json.dumps(record.typing_metadata_json)


def test_explode_pause_features_filters_non_empty_events() -> None:
	payload = [
		{"pause_events": [{"start_timestamp_ms": 0, "duration_ms": 100}]},
		{"pause_events": []},
		{},
	]

	frame = metrics.explode_pause_features(payload)

	assert len(frame) == 1
	assert frame.iloc[0]["pause_events"][0]["duration_ms"] == 100


def test_compute_typing_metrics_handles_string_metadata() -> None:
	metadata = {
		"keystroke_events": [{"key": "a"}, {"key": "b"}],
		"total_duration_ms": 2000,
	}
	row = pd.Series(
		{
			"user_prompt_text": "two words",
			"typing_metadata_json": json.dumps(metadata),
		}
	)

	result = metrics.compute_typing_metrics(row)

	assert result["keystroke_count"] == 2
	assert result["duration_ms"] == 2000
	assert result["words_per_minute"] == pytest.approx(60.0)
