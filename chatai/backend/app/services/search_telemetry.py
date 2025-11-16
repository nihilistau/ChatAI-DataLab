"""Expose aggregated search telemetry stats for Ops Deck consumers."""
# @tag: backend,services,telemetry

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from datalab.scripts import search_telemetry as telemetry
DEFAULT_DB = REPO_ROOT / "data" / "search_telemetry.db"
DEFAULT_PRESET_TAGS = REPO_ROOT / telemetry.DEFAULT_PRESET_TAGS_PATH


def _resolve_db_path(db_path: Path | str | None) -> Path:
    if db_path is None:
        return DEFAULT_DB
    return Path(db_path)


def _safe_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(slots=True)
class TelemetrySummary:
    total_runs: int
    runs_last_24h: int
    runs_with_matches: int
    avg_duration_ms: float | None
    avg_match_density: float | None
    last_ingest_at: datetime | None
    top_patterns: list[dict[str, Any]]

    def to_dict(self, match_rate: float) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "runs_last_24h": self.runs_last_24h,
            "runs_with_matches": self.runs_with_matches,
            "avg_duration_ms": self.avg_duration_ms,
            "avg_match_density": self.avg_match_density,
            "last_ingest_at": self.last_ingest_at.isoformat() if self.last_ingest_at else None,
            "match_rate": match_rate,
            "top_patterns": self.top_patterns,
        }


def get_search_telemetry_summary(
    db_path: Path | str | None = None,
    *,
    top_n: int = 5,
    recent_hours: int = 24,
    preset_drift_lookback: int = 50,
    preset_tags_path: Path | str | None = None,
) -> dict[str, Any]:
    path = _resolve_db_path(db_path)
    if not path.exists():
        return {
            "total_runs": 0,
            "runs_last_24h": 0,
            "runs_with_matches": 0,
            "avg_duration_ms": None,
            "avg_match_density": None,
            "last_ingest_at": None,
            "match_rate": 0.0,
            "top_patterns": [],
            "preset_drift": [],
        }

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        aggregate = conn.execute(
            """
            SELECT
                COUNT(*) AS total_runs,
                SUM(CASE WHEN matches > 0 THEN 1 ELSE 0 END) AS runs_with_matches,
                AVG(duration_ms) AS avg_duration_ms,
                AVG(
                    CASE WHEN files_scanned > 0 THEN CAST(matches AS REAL) / files_scanned
                         ELSE 0 END
                ) AS avg_match_density,
                MAX(timestamp) AS last_timestamp
            FROM search_runs
            """
        ).fetchone()

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=recent_hours)).isoformat()
        runs_last_24h = conn.execute(
            "SELECT COUNT(*) FROM search_runs WHERE timestamp >= ?",
            (cutoff,),
        ).fetchone()[0]

        top_patterns_rows = conn.execute(
            """
            SELECT
                COALESCE(pattern, 'custom/adhoc') AS pattern,
                COUNT(*) AS runs,
                SUM(matches) AS total_matches,
                AVG(files_scanned) AS avg_files_scanned
            FROM search_runs
            WHERE pattern IS NOT NULL AND pattern <> ''
            GROUP BY pattern
            ORDER BY total_matches DESC, runs DESC
            LIMIT ?
            """,
            (top_n,),
        ).fetchall()
    finally:
        conn.close()

    total_runs = int(aggregate["total_runs"] or 0)
    runs_with_matches = int(aggregate["runs_with_matches"] or 0)
    avg_duration_ms = float(aggregate["avg_duration_ms"]) if aggregate["avg_duration_ms"] is not None else None
    avg_match_density = (
        float(aggregate["avg_match_density"]) if aggregate["avg_match_density"] is not None else None
    )
    last_ingest_at = _safe_datetime(aggregate["last_timestamp"])

    top_patterns = [
        {
            "pattern": row["pattern"],
            "runs": int(row["runs"] or 0),
            "total_matches": int(row["total_matches"] or 0),
            "avg_files_scanned": float(row["avg_files_scanned"] or 0),
        }
        for row in top_patterns_rows
    ]

    summary = TelemetrySummary(
        total_runs=total_runs,
        runs_last_24h=int(runs_last_24h or 0),
        runs_with_matches=runs_with_matches,
        avg_duration_ms=avg_duration_ms,
        avg_match_density=avg_match_density,
        last_ingest_at=last_ingest_at,
        top_patterns=top_patterns,
    )
    match_rate = (runs_with_matches / total_runs) if total_runs else 0.0
    preset_tags_candidate = preset_tags_path or DEFAULT_PRESET_TAGS
    preset_drift = telemetry.compute_preset_drift(
        path,
        lookback=preset_drift_lookback,
        preset_tags_path=preset_tags_candidate,
    )

    summary_dict = summary.to_dict(match_rate)
    summary_dict["preset_drift"] = preset_drift
    return summary_dict
