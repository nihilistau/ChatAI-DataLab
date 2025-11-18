"""Expose aggregated search telemetry stats for Ops Deck consumers."""
# @tag: backend,services,telemetry

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from kitchen.telemetry import search_ledger as ledger

DEFAULT_LEDGER = REPO_ROOT / "data" / "search_telemetry.json"
DEFAULT_PRESET_TAGS = REPO_ROOT / "configs" / "search_preset_tags.json"


def _resolve_ledger_path(summary_path: Path | str | None) -> Path:
    if summary_path is None:
        return DEFAULT_LEDGER
    return Path(summary_path)


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


def _count_recent_runs(runs: list[dict[str, Any]], *, recent_hours: int) -> int:
    window = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    total = 0
    for entry in runs:
        timestamp = _safe_datetime(entry.get("timestamp")) if isinstance(entry, dict) else None
        if timestamp and timestamp >= window:
            total += 1
    return total


def _resolve_match_stats(summary: dict[str, Any]) -> tuple[int, int, float | None, float | None, datetime | None]:
    total_runs = int(summary.get("total_runs") or 0)
    runs_with_matches = int(summary.get("runs_with_matches") or 0)
    avg_duration = summary.get("avg_duration_ms")
    avg_density = summary.get("avg_match_density")
    last_ingest = _safe_datetime(summary.get("last_ingest_at"))
    return total_runs, runs_with_matches, avg_duration, avg_density, last_ingest


def get_search_telemetry_summary(
    db_path: Path | str | None = None,
    *,
    top_n: int = 5,
    recent_hours: int = 24,
    preset_drift_lookback: int = 50,
    preset_tags_path: Path | str | None = None,
) -> dict[str, Any]:
    path = _resolve_ledger_path(db_path)
    summary_payload = ledger.read_summary(path)
    if not summary_payload:
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

    total_runs, runs_with_matches, avg_duration, avg_density, last_ingest = _resolve_match_stats(summary_payload)
    runs_payload = summary_payload.get("runs", []) if isinstance(summary_payload, dict) else []
    runs_last_24h = _count_recent_runs(runs_payload if isinstance(runs_payload, list) else [], recent_hours=recent_hours)
    top_patterns = list(summary_payload.get("top_patterns", []) or [])[:top_n]
    preset_tags_candidate = preset_tags_path or DEFAULT_PRESET_TAGS
    preset_drift = ledger.compute_preset_drift_from_summary(
        path,
        lookback=preset_drift_lookback,
        preset_tags_path=preset_tags_candidate,
    )

    summary = TelemetrySummary(
        total_runs=total_runs,
        runs_last_24h=runs_last_24h,
        runs_with_matches=runs_with_matches,
        avg_duration_ms=avg_duration,
        avg_match_density=avg_density,
        last_ingest_at=last_ingest,
        top_patterns=top_patterns,
    )
    summary_dict = summary.to_dict(match_rate=(runs_with_matches / total_runs) if total_runs else 0.0)
    summary_dict["preset_drift"] = preset_drift
    return summary_dict
