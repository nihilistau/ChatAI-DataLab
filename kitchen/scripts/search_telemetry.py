"""Kitchen-first facade over the search telemetry ledger helpers."""
# @tag: kitchen,scripts,telemetry

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from kitchen.telemetry import search_ledger as ledger

DEFAULT_LOG_PATH = ledger.DEFAULT_LOG_PATH
DEFAULT_SUMMARY_PATH = ledger.DEFAULT_SUMMARY_PATH
DEFAULT_PRESET_TAGS_PATH = ledger.DEFAULT_PRESET_TAGS
DEFAULT_RUNS_PARQUET_PATH = ledger.DEFAULT_RUNS_PARQUET_PATH
DEFAULT_DAILY_PARQUET_PATH = ledger.DEFAULT_DAILY_PARQUET_PATH


@dataclass(slots=True)
class IngestStats:
	total_runs: int
	inserted: int
	previous_total: int
	summary: dict[str, Any]
	artifacts: tuple[str, ...] = ()

	@property
	def duplicates(self) -> int:
		return max(self.previous_total, 0)

	def as_dict(self) -> dict[str, Any]:
		return {
			"total_runs": self.total_runs,
			"inserted": self.inserted,
			"previous_total": self.previous_total,
			"summary": self.summary,
			"artifacts": list(self.artifacts),
		}


def _ensure_dataframe(values: Iterable[dict[str, Any]], *, columns: list[str]) -> pd.DataFrame:
	data = list(values)
	if not data:
		return pd.DataFrame(columns=columns)
	frame = pd.DataFrame(data)
	for column in columns:
		if column not in frame.columns:
			frame[column] = pd.NA
	return frame[columns]


def ingest_search_history(
	log_path: Path | str = DEFAULT_LOG_PATH,
	db_path: Path | str = DEFAULT_SUMMARY_PATH,
	*,
	preset_tags_path: Path | str | None = None,
	lookback: int = 50,
	runs_parquet_path: Path | str | None = None,
	daily_parquet_path: Path | str | None = None,
	emit_tail_log: bool = True,
) -> IngestStats:
	output = Path(db_path)
	previous_summary = ledger.read_summary(output)
	previous_total = int(previous_summary.get("total_runs") or 0)
	summary = ledger.ingest_search_history(
		log_path,
		output_path=output,
		preset_tags_path=preset_tags_path,
		lookback=lookback,
		runs_parquet_path=runs_parquet_path,
		daily_parquet_path=daily_parquet_path,
		emit_tail_log=emit_tail_log,
	)
	total_runs = int(summary.get("total_runs") or 0)
	inserted = max(total_runs - previous_total, 0)
	artifacts: list[str] = [str(output)]
	if runs_parquet_path:
		artifacts.append(str(Path(runs_parquet_path)))
	if daily_parquet_path:
		artifacts.append(str(Path(daily_parquet_path)))
	return IngestStats(
		total_runs=total_runs,
		inserted=inserted,
		previous_total=previous_total,
		summary=summary,
		artifacts=tuple(artifacts),
	)


def migrate_from_sqlite(
	db_path: Path | str,
	output_path: Path | str = DEFAULT_SUMMARY_PATH,
	*,
	preset_tags_path: Path | str | None = None,
	lookback: int = 50,
	runs_parquet_path: Path | str | None = None,
	daily_parquet_path: Path | str | None = None,
	emit_tail_log: bool = True,
) -> dict[str, Any]:
	return ledger.migrate_from_sqlite(
		db_path,
		output_path=output_path,
		preset_tags_path=preset_tags_path,
		lookback=lookback,
		runs_parquet_path=runs_parquet_path,
		daily_parquet_path=daily_parquet_path,
		emit_tail_log=emit_tail_log,
	)


def read_summary(path: Path | str = DEFAULT_SUMMARY_PATH) -> dict[str, Any]:
	return ledger.read_summary(path)


def write_summary(summary: dict[str, Any], path: Path | str = DEFAULT_SUMMARY_PATH) -> Path:
	return ledger.write_summary(summary, path)


def load_search_runs(db_path: Path | str = DEFAULT_SUMMARY_PATH) -> pd.DataFrame:
	records = ledger.load_runs(db_path)
	frame = _ensure_dataframe(
		records,
		columns=["timestamp", "pattern", "preset", "files_scanned", "matches", "duration_ms"],
	)
	return frame


def load_daily_metrics(db_path: Path | str = DEFAULT_SUMMARY_PATH) -> pd.DataFrame:
	metrics = ledger.load_daily_metrics(db_path)
	return _ensure_dataframe(
		metrics,
		columns=[
			"event_date",
			"runs",
			"files_scanned",
			"matches",
			"runs_with_matches",
			"avg_duration_ms",
			"avg_match_density",
		],
	)


def compute_preset_drift(
	db_path: Path | str = DEFAULT_SUMMARY_PATH,
	*,
	lookback: int = 50,
	preset_tags_path: Path | str | None = None,
) -> list[dict[str, Any]]:
	return ledger.compute_preset_drift_from_summary(
		db_path,
		lookback=lookback,
		preset_tags_path=preset_tags_path,
	)
