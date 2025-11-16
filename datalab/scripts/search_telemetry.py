"""Utilities for hydrating Search Toolkit logs into SQLite and pandas-friendly tables."""
# @tag: datalab,scripts,telemetry

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Any, Dict, Tuple

from datalab.lab_paths import data_path, lab_path

DEFAULT_LOG = lab_path("logs", "search-history.jsonl")
DEFAULT_DB = data_path("search_telemetry.db")
DEFAULT_PRESET_TAGS_PATH = lab_path("configs", "search_preset_tags.json")

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_hash TEXT UNIQUE,
            timestamp TEXT NOT NULL,
            pattern TEXT,
            preset TEXT,
            regex INTEGER,
            case_sensitive INTEGER,
            root TEXT,
            recursive INTEGER,
            include_files TEXT,
            exclude_patterns TEXT,
            files_scanned INTEGER,
            matches INTEGER,
            duration_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_daily_metrics (
            event_date TEXT PRIMARY KEY,
            runs INTEGER NOT NULL,
            files_scanned INTEGER NOT NULL,
            matches INTEGER NOT NULL,
            runs_with_matches INTEGER NOT NULL,
            avg_duration_ms REAL NOT NULL,
            avg_match_density REAL NOT NULL
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_search_runs_timestamp ON search_runs(timestamp)"""
    )


def _load_lines(log_path: Path) -> List[tuple[str, dict]]:
    if not log_path.exists():
        return []

    entries: List[tuple[str, dict]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append((line, payload))
    return entries


def _compute_hash(raw_line: str) -> str:
    return hashlib.sha256(raw_line.encode("utf-8")).hexdigest()


def _normalize_datetime(timestamp: str | None) -> str:
    if not timestamp:
        return datetime.utcnow().isoformat()
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.isoformat()
    except ValueError:
        return datetime.utcnow().isoformat()


def _json_or_none(values: Sequence[str] | None) -> str | None:
    if not values:
        return None
    return json.dumps(values)


@dataclass
class IngestStats:
    inserted: int
    skipped: int
    total: int

    def as_dict(self) -> dict:
        return {"inserted": self.inserted, "skipped": self.skipped, "total": self.total}


@dataclass
class PresetDrift:
    preset: str
    tags: list[str]
    total_runs: int
    recent_runs: int
    match_rate_lifetime: float
    match_rate_recent: float
    avg_duration_lifetime: float
    avg_duration_recent: float
    avg_density_lifetime: float
    avg_density_recent: float
    delta_match_rate: float
    delta_duration_ms: float
    delta_density: float
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "preset": self.preset,
            "tags": self.tags,
            "total_runs": self.total_runs,
            "recent_runs": self.recent_runs,
            "match_rate_lifetime": self.match_rate_lifetime,
            "match_rate_recent": self.match_rate_recent,
            "avg_duration_lifetime": self.avg_duration_lifetime,
            "avg_duration_recent": self.avg_duration_recent,
            "avg_density_lifetime": self.avg_density_lifetime,
            "avg_density_recent": self.avg_density_recent,
            "delta_match_rate": self.delta_match_rate,
            "delta_duration_ms": self.delta_duration_ms,
            "delta_density": self.delta_density,
            "status": self.status,
        }


def ingest_search_history(log_path: Path = DEFAULT_LOG, db_path: Path = DEFAULT_DB) -> IngestStats:
    log_path = Path(log_path)
    db_path = Path(db_path)
    _ensure_parent(db_path)

    rows = _load_lines(log_path)
    conn = sqlite3.connect(db_path)
    inserted = 0
    skipped = 0
    try:
        _ensure_schema(conn)
        for raw_line, payload in rows:
            entry_hash = _compute_hash(raw_line)
            normalized_ts = _normalize_datetime(payload.get("timestamp"))
            include_files = payload.get("includeFiles")
            exclude_patterns = payload.get("excludePatterns")
            try:
                conn.execute(
                    """
                    INSERT INTO search_runs (
                        entry_hash, timestamp, pattern, preset, regex, case_sensitive,
                        root, recursive, include_files, exclude_patterns,
                        files_scanned, matches, duration_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_hash,
                        normalized_ts,
                        payload.get("pattern"),
                        payload.get("preset"),
                        int(bool(payload.get("regex"))),
                        int(bool(payload.get("caseSensitive"))),
                        payload.get("root"),
                        int(bool(payload.get("recursive", True))),
                        _json_or_none(include_files),
                        _json_or_none(exclude_patterns),
                        int(payload.get("filesScanned") or 0),
                        int(payload.get("matches") or 0),
                        int(payload.get("durationMs") or 0),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
                continue
        _refresh_daily_metrics(conn)
        conn.commit()
    finally:
        conn.close()

    total = inserted + skipped
    return IngestStats(inserted=inserted, skipped=skipped, total=total)


def _refresh_daily_metrics(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM search_daily_metrics")
    conn.execute(
        """
        INSERT INTO search_daily_metrics (
            event_date, runs, files_scanned, matches,
            runs_with_matches, avg_duration_ms, avg_match_density
        )
        SELECT
            substr(timestamp, 1, 10) as event_date,
            COUNT(*) as runs,
            SUM(files_scanned) as files_scanned,
            SUM(matches) as matches,
            SUM(CASE WHEN matches > 0 THEN 1 ELSE 0 END) as runs_with_matches,
            AVG(duration_ms) as avg_duration_ms,
            AVG(
                CASE WHEN files_scanned > 0 THEN CAST(matches AS REAL) / files_scanned
                     ELSE 0 END
            ) as avg_match_density
        FROM search_runs
        GROUP BY event_date
        ORDER BY event_date
        """
    )


def load_preset_tags(path: Path | str | None = None) -> dict[str, list[str]]:
    """Load preset → tags mapping from disk.

    Accepts either a bare mapping (preset -> tag or list of tags) or an object containing
    {"preset_tags": {...}}. Missing files result in an empty mapping.
    """

    candidate = Path(path) if path else DEFAULT_PRESET_TAGS_PATH
    if not candidate.exists():
        return {}

    try:
        with candidate.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):  # pragma: no cover - defensive guard
        return {}

    mapping: dict[str, Any]
    if isinstance(payload, dict) and "preset_tags" in payload:
        mapping = payload.get("preset_tags", {}) or {}
    elif isinstance(payload, dict):
        mapping = payload
    else:
        return {}

    normalized: dict[str, list[str]] = {}
    for preset, tags in mapping.items():
        if not isinstance(preset, str):
            continue
        if tags is None:
            normalized[preset] = []
        elif isinstance(tags, str):
            normalized[preset] = [tags]
        elif isinstance(tags, list):
            normalized[preset] = [str(tag) for tag in tags if isinstance(tag, str)]
        else:
            normalized[preset] = [str(tags)]
    return normalized


def _aggregate_runs(rows: list[sqlite3.Row]) -> tuple[int, int, float, float]:
    total_runs = len(rows)
    if total_runs == 0:
        return 0, 0, 0.0, 0.0

    runs_with_matches = sum(1 for row in rows if (row["matches"] or 0) > 0)
    avg_duration = sum(float(row["duration_ms"] or 0) for row in rows) / total_runs
    avg_density = 0.0
    for row in rows:
        files = row["files_scanned"] or 0
        matches = row["matches"] or 0
        avg_density += (matches / files) if files else 0.0
    avg_density /= total_runs
    return total_runs, runs_with_matches, avg_duration, avg_density


def compute_preset_drift(
    db_path: Path | str = DEFAULT_DB,
    *,
    lookback: int = 50,
    preset_tags: dict[str, list[str]] | None = None,
    preset_tags_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Compare recent preset performance against lifetime averages."""

    path = Path(db_path)
    if not path.exists():
        return []

    tags_map = preset_tags or load_preset_tags(preset_tags_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        lifetime_rows = conn.execute(
            """
            SELECT
                preset,
                COUNT(*) AS total_runs,
                SUM(CASE WHEN matches > 0 THEN 1 ELSE 0 END) AS runs_with_matches,
                AVG(duration_ms) AS avg_duration_ms,
                AVG(
                    CASE WHEN files_scanned > 0 THEN CAST(matches AS REAL) / files_scanned
                         ELSE 0 END
                ) AS avg_density
            FROM search_runs
            WHERE preset IS NOT NULL AND preset <> ''
            GROUP BY preset
            """
        ).fetchall()

        per_run_rows = conn.execute(
            """
            SELECT preset, timestamp, matches, files_scanned, duration_ms
            FROM search_runs
            WHERE preset IS NOT NULL AND preset <> ''
            ORDER BY timestamp DESC
            """
        ).fetchall()
    finally:
        conn.close()

    lifetime_map: dict[str, dict[str, float]] = {}
    for row in lifetime_rows:
        preset = row["preset"]
        if not preset:
            continue
        total_runs = int(row["total_runs"] or 0)
        if total_runs == 0:
            continue
        lifetime_map[preset] = {
            "total_runs": total_runs,
            "runs_with_matches": int(row["runs_with_matches"] or 0),
            "avg_duration": float(row["avg_duration_ms"] or 0.0),
            "avg_density": float(row["avg_density"] or 0.0),
        }

    recent_rows: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in per_run_rows:
        preset = row["preset"]
        bucket = recent_rows[preset]
        if len(bucket) >= lookback:
            continue
        bucket.append(row)

    results: list[PresetDrift] = []
    for preset, lifetime_stats in lifetime_map.items():
        lifetime_total = lifetime_stats["total_runs"]
        lifetime_with_matches = lifetime_stats["runs_with_matches"]
        lifetime_match_rate = lifetime_with_matches / lifetime_total if lifetime_total else 0.0
        lifetime_duration = lifetime_stats["avg_duration"]
        lifetime_density = lifetime_stats["avg_density"]

        recent_sample = recent_rows.get(preset, [])
        recent_total, recent_with_matches, recent_duration, recent_density = _aggregate_runs(recent_sample)
        recent_match_rate = (
            recent_with_matches / recent_total if recent_total else lifetime_match_rate
        )

        delta_match_rate = recent_match_rate - lifetime_match_rate
        delta_duration = recent_duration - lifetime_duration
        delta_density = recent_density - lifetime_density

        status = "stable"
        if recent_total >= max(3, int(lookback * 0.2)):
            if delta_match_rate <= -0.15 or delta_density <= -0.15:
                status = "regressing"
            elif delta_match_rate >= 0.1 or delta_density >= 0.1:
                status = "improving"

        drift_entry = PresetDrift(
            preset=preset,
            tags=tags_map.get(preset, []),
            total_runs=lifetime_total,
            recent_runs=recent_total,
            match_rate_lifetime=round(lifetime_match_rate, 4),
            match_rate_recent=round(recent_match_rate, 4),
            avg_duration_lifetime=round(lifetime_duration, 2),
            avg_duration_recent=round(recent_duration, 2),
            avg_density_lifetime=round(lifetime_density, 4),
            avg_density_recent=round(recent_density, 4),
            delta_match_rate=round(delta_match_rate, 4),
            delta_duration_ms=round(delta_duration, 2),
            delta_density=round(delta_density, 4),
            status=status,
        )
        results.append(drift_entry)

    return [entry.as_dict() for entry in sorted(results, key=lambda entry: entry.delta_match_rate)]


def load_search_runs(db_path: Path = DEFAULT_DB, limit: int | None = None):  # pragma: no cover
    import pandas as pd

    db_path = Path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT * FROM search_runs ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {int(limit)}"
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def load_daily_metrics(db_path: Path = DEFAULT_DB):  # pragma: no cover
    import pandas as pd

    db_path = Path(db_path)
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM search_daily_metrics ORDER BY event_date DESC",
            conn,
        )
    finally:
        conn.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hydrate search telemetry into SQLite")
    subparsers = parser.add_subparsers(dest="command", required=False)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest search history into SQLite")
    ingest_parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG)
    ingest_parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)

    stats_parser = subparsers.add_parser("stats", help="Print aggregated telemetry stats")
    stats_parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    stats_parser.add_argument("--limit", type=int, default=10)

    parser.set_defaults(command="ingest")
    return parser


def _cmd_ingest(args: argparse.Namespace) -> int:
    stats = ingest_search_history(args.log_path, args.db_path)
    print(f"Inserted {stats.inserted} new run(s); skipped {stats.skipped} duplicates.")
    if stats.total == 0:
        print("No log entries were found.")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM search_daily_metrics ORDER BY event_date DESC LIMIT ?",
            (args.limit,),
        )
        rows = cursor.fetchall()
        headers = [description[0] for description in cursor.description]
    finally:
        conn.close()

    if not rows:
        print("No telemetry has been ingested yet. Run the ingest command first.")
        return 0

    column_widths = [max(len(str(value)) for value in [header] + [row[idx] for row in rows]) for idx, header in enumerate(headers)]
    header_line = " | ".join(header.ljust(column_widths[idx]) for idx, header in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print(" | ".join(str(value).ljust(column_widths[idx]) for idx, value in enumerate(row)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "stats":
        return _cmd_stats(args)
    return _cmd_ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
