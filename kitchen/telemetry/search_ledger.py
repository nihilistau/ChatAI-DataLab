from __future__ import annotations

"""Search telemetry ingestion + ledger helpers (JSON-first, SQLite-free)."""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from kitchen.lab_paths import data_path, lab_path

LAB_ROOT = lab_path()
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))

from playground.backend.app.schemas import TailLogEntryCreate
from playground.backend.app.services.data_store import data_store_context

DEFAULT_LOG_PATH = lab_path("logs", "search-history.jsonl")
DEFAULT_SUMMARY_PATH = data_path("search_telemetry.json")
DEFAULT_PRESET_TAGS = lab_path("configs", "search_preset_tags.json")
DEFAULT_RUNS_PARQUET_PATH = data_path("search_telemetry-runs.parquet")
DEFAULT_DAILY_PARQUET_PATH = data_path("search_telemetry-daily.parquet")

_RUN_PARQUET_SCHEMA = {
    "timestamp": "string",
    "pattern": "string",
    "preset": "string",
    "files_scanned": "int64",
    "matches": "int64",
    "duration_ms": "int64",
}

_DAILY_PARQUET_SCHEMA = {
    "event_date": "string",
    "runs": "int64",
    "files_scanned": "int64",
    "matches": "int64",
    "runs_with_matches": "int64",
    "avg_duration_ms": "float64",
    "avg_match_density": "float64",
}


def _emit_tail_log(message: str) -> None:
    """Best-effort tail log emission for search telemetry events."""

    try:
        with data_store_context() as store:
            store.create_tail_log_entry(
                TailLogEntryCreate(message=message, source="search-ledger")
            )
    except Exception:
        # Observability shouldn't break ingestion; ignore failures.
        return


def _log_summary(summary: dict[str, Any], *, action: str) -> None:
    total_runs = summary.get("total_runs", 0)
    last_day = summary.get("runs_last_24h", 0)
    match_rate = summary.get("match_rate", 0.0) or 0.0
    message = (
        f"{action}: {total_runs} runs (24h {last_day}) · match-rate {match_rate:.2f}"
    )
    _emit_tail_log(message)


@dataclass(slots=True)
class RunRecord:
    """Normalized representation of a single search run."""

    timestamp: datetime
    pattern: str | None
    preset: str | None
    files_scanned: int
    matches: int
    duration_ms: int

    @property
    def iso_timestamp(self) -> str:
        return self.timestamp.isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.iso_timestamp,
            "pattern": self.pattern,
            "preset": self.preset,
            "files_scanned": self.files_scanned,
            "matches": self.matches,
            "duration_ms": self.duration_ms,
        }


def _normalize_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    candidate = value
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_lines(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw_line = raw.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            entries.append(payload)
    return entries


def _normalize_run(payload: dict[str, Any]) -> RunRecord:
    return RunRecord(
        timestamp=_normalize_timestamp(payload.get("timestamp")),
        pattern=payload.get("pattern"),
        preset=payload.get("preset"),
        files_scanned=int(payload.get("filesScanned") or payload.get("files_scanned") or 0),
        matches=int(payload.get("matches") or 0),
        duration_ms=int(payload.get("durationMs") or payload.get("duration_ms") or 0),
    )


def _build_runs_from_log(log_path: Path) -> list[RunRecord]:
    return [_normalize_run(payload) for payload in _load_lines(log_path)]


def _record_from_summary(payload: dict[str, Any]) -> RunRecord:
    return RunRecord(
        timestamp=_normalize_timestamp(payload.get("timestamp")),
        pattern=payload.get("pattern"),
        preset=payload.get("preset"),
        files_scanned=int(payload.get("files_scanned") or 0),
        matches=int(payload.get("matches") or 0),
        duration_ms=int(payload.get("duration_ms") or 0),
    )


def _build_runs_from_sqlite(db_path: Path) -> list[RunRecord]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT timestamp, pattern, preset, files_scanned, matches, duration_ms FROM search_runs"
        ).fetchall()
    finally:
        conn.close()
    runs: list[RunRecord] = []
    for row in rows:
        runs.append(
            RunRecord(
                timestamp=_normalize_timestamp(row["timestamp"]),
                pattern=row["pattern"],
                preset=row["preset"],
                files_scanned=int(row["files_scanned"] or 0),
                matches=int(row["matches"] or 0),
                duration_ms=int(row["duration_ms"] or 0),
            )
        )
    return runs


def _load_preset_tags(path: Path | None) -> dict[str, list[str]]:
    candidate = path if path else DEFAULT_PRESET_TAGS
    if not candidate.exists():
        return {}
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
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


def _compute_top_patterns(runs: Iterable[RunRecord], *, top_n: int = 5) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "total_matches": 0, "files": 0})
    for run in runs:
        if not run.pattern:
            key = "custom/adhoc"
        else:
            key = run.pattern
        bucket = buckets[key]
        bucket["runs"] += 1
        bucket["total_matches"] += run.matches
        bucket["files"] += run.files_scanned
    ranked = sorted(
        (
            {
                "pattern": pattern,
                "runs": data["runs"],
                "total_matches": data["total_matches"],
                "avg_files_scanned": (data["files"] / data["runs"]) if data["runs"] else 0.0,
            }
            for pattern, data in buckets.items()
        ),
        key=lambda entry: (entry["total_matches"], entry["runs"]),
        reverse=True,
    )
    return ranked[:top_n]


def _aggregate_daily_metrics(runs: Iterable[RunRecord]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "runs": 0,
        "files_scanned": 0,
        "matches": 0,
        "runs_with_matches": 0,
        "duration_sum": 0.0,
        "density_sum": 0.0,
    })
    for run in runs:
        key = run.timestamp.date().isoformat()
        bucket = buckets[key]
        bucket["runs"] += 1
        bucket["files_scanned"] += run.files_scanned
        bucket["matches"] += run.matches
        if run.matches > 0:
            bucket["runs_with_matches"] += 1
        bucket["duration_sum"] += float(run.duration_ms)
        density = (run.matches / run.files_scanned) if run.files_scanned else 0.0
        bucket["density_sum"] += density
    return [
        {
            "event_date": day,
            "runs": data["runs"],
            "files_scanned": data["files_scanned"],
            "matches": data["matches"],
            "runs_with_matches": data["runs_with_matches"],
            "avg_duration_ms": (data["duration_sum"] / data["runs"]) if data["runs"] else 0.0,
            "avg_match_density": (data["density_sum"] / data["runs"]) if data["runs"] else 0.0,
        }
        for day, data in sorted(buckets.items())
    ]


def _aggregate_runs(runs: Sequence[RunRecord]) -> tuple[int, int, float, float]:
    total_runs = len(runs)
    if total_runs == 0:
        return 0, 0, 0.0, 0.0
    runs_with_matches = sum(1 for run in runs if run.matches > 0)
    avg_duration = sum(run.duration_ms for run in runs) / total_runs
    avg_density = 0.0
    for run in runs:
        if run.files_scanned:
            avg_density += run.matches / run.files_scanned
    avg_density /= total_runs
    return total_runs, runs_with_matches, avg_duration, avg_density


def _compute_preset_drift(
    runs: list[RunRecord],
    *,
    lookback: int,
    preset_tags: dict[str, list[str]],
) -> list[dict[str, Any]]:
    per_preset: dict[str, list[RunRecord]] = defaultdict(list)
    for run in runs:
        if not run.preset:
            continue
        per_preset[run.preset].append(run)

    recent_samples: dict[str, list[RunRecord]] = {}
    lifetime_stats: dict[str, tuple[int, int, float, float]] = {}

    for preset, bucket in per_preset.items():
        ordered = sorted(bucket, key=lambda run: run.timestamp, reverse=True)
        lifetime_stats[preset] = _aggregate_runs(bucket)
        recent_samples[preset] = ordered[:lookback]

    drift_entries: list[dict[str, Any]] = []
    for preset, lifetime in lifetime_stats.items():
        lifetime_total, lifetime_with_matches, lifetime_duration, lifetime_density = lifetime
        if lifetime_total == 0:
            continue
        lifetime_match_rate = lifetime_with_matches / lifetime_total if lifetime_total else 0.0
        recent_total, recent_with_matches, recent_duration, recent_density = _aggregate_runs(
            recent_samples.get(preset, [])
        )
        recent_match_rate = (
            recent_with_matches / recent_total if recent_total else lifetime_match_rate
        )
        delta_match_rate = recent_match_rate - lifetime_match_rate
        delta_duration = recent_duration - lifetime_duration
        delta_density = recent_density - lifetime_density

        status = "stable"
        threshold = max(3, int(lookback * 0.2))
        if recent_total >= threshold:
            if delta_match_rate <= -0.15 or delta_density <= -0.15:
                status = "regressing"
            elif delta_match_rate >= 0.1 or delta_density >= 0.1:
                status = "improving"

        drift_entries.append(
            {
                "preset": preset,
                "tags": preset_tags.get(preset, []),
                "total_runs": lifetime_total,
                "recent_runs": recent_total,
                "match_rate_lifetime": round(lifetime_match_rate, 4),
                "match_rate_recent": round(recent_match_rate, 4),
                "avg_duration_lifetime": round(lifetime_duration, 2),
                "avg_duration_recent": round(recent_duration, 2),
                "avg_density_lifetime": round(lifetime_density, 4),
                "avg_density_recent": round(recent_density, 4),
                "delta_match_rate": round(delta_match_rate, 4),
                "delta_duration_ms": round(delta_duration, 2),
                "delta_density": round(delta_density, 4),
                "status": status,
            }
        )

    return sorted(drift_entries, key=lambda entry: entry["delta_match_rate"])


def _build_summary(
    runs: list[RunRecord],
    *,
    log_path: Path,
    preset_tags_path: Path | None,
    lookback: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    total_runs = len(runs)
    runs_with_matches = sum(1 for run in runs if run.matches > 0)
    runs_last_24h = sum(1 for run in runs if (current_time - run.timestamp) <= timedelta(hours=24))
    avg_duration = (sum(run.duration_ms for run in runs) / total_runs) if total_runs else None
    avg_density = (
        sum((run.matches / run.files_scanned) if run.files_scanned else 0.0 for run in runs) / total_runs
        if total_runs
        else None
    )
    last_ingest = max((run.timestamp for run in runs), default=None)
    preset_tags = _load_preset_tags(preset_tags_path)

    summary = {
        "generated_at": current_time.isoformat(),
        "source_log": str(log_path),
        "total_runs": total_runs,
        "runs_with_matches": runs_with_matches,
        "runs_last_24h": runs_last_24h,
        "avg_duration_ms": round(avg_duration, 2) if avg_duration is not None else None,
        "avg_match_density": round(avg_density, 4) if avg_density is not None else None,
        "last_ingest_at": last_ingest.isoformat() if last_ingest else None,
        "match_rate": (runs_with_matches / total_runs) if total_runs else 0.0,
        "top_patterns": _compute_top_patterns(runs),
        "daily_metrics": _aggregate_daily_metrics(runs),
        "preset_drift": _compute_preset_drift(runs, lookback=lookback, preset_tags=preset_tags),
        "runs": [run.to_dict() for run in runs],
        "metadata": {
            "log_entries": total_runs,
            "log_path": str(log_path),
            "preset_tags_path": str(preset_tags_path) if preset_tags_path else None,
        },
    }
    return summary


def write_summary(summary: dict[str, Any], path: Path | str = DEFAULT_SUMMARY_PATH) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return target


def read_summary(path: Path | str = DEFAULT_SUMMARY_PATH) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_runs(summary_path: Path | str = DEFAULT_SUMMARY_PATH) -> list[dict[str, Any]]:
    summary = read_summary(summary_path)
    runs = summary.get("runs", [])
    if not isinstance(runs, list):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in runs:
        if isinstance(entry, dict):
            normalized.append(
                {
                    "timestamp": entry.get("timestamp"),
                    "pattern": entry.get("pattern"),
                    "preset": entry.get("preset"),
                    "files_scanned": int(entry.get("files_scanned") or 0),
                    "matches": int(entry.get("matches") or 0),
                    "duration_ms": int(entry.get("duration_ms") or 0),
                }
            )
    return normalized


def load_daily_metrics(summary_path: Path | str = DEFAULT_SUMMARY_PATH) -> list[dict[str, Any]]:
    summary = read_summary(summary_path)
    metrics = summary.get("daily_metrics", [])
    if isinstance(metrics, list):
        return [metric for metric in metrics if isinstance(metric, dict)]
    return []


def _resolve_arrow_type(label: str, pa_module: Any):  # pragma: no cover - exercised via parquet helpers
    if label == "string":
        return pa_module.string()
    if label == "int64":
        return pa_module.int64()
    if label == "float64":
        return pa_module.float64()
    raise ValueError(f"Unsupported Arrow type label: {label}")


def _normalize_records(records: Iterable[dict[str, Any]], schema: dict[str, str]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        normalized.append({key: record.get(key) for key in schema})
    return normalized


def _write_parquet_table(
    records: Iterable[dict[str, Any]],
    path: Path,
    schema: dict[str, str],
    pa_module: Any,
    pq_module: Any,
) -> Path:
    normalized = _normalize_records(records, schema)
    columns: dict[str, Any] = {}
    for column, label in schema.items():
        column_type = _resolve_arrow_type(label, pa_module)
        values = [entry.get(column) for entry in normalized]
        columns[column] = pa_module.array(values, type=column_type)
    table = pa_module.table(columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq_module.write_table(table, path)
    return path


def _write_parquet_tables(
    summary: dict[str, Any],
    *,
    runs_path: Path | None,
    daily_path: Path | None,
) -> list[Path]:
    targets: list[Path] = []
    if not runs_path and not daily_path:
        return targets
    try:  # pragma: no cover - import path only executed when exports requested
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "Parquet export requires the optional 'pyarrow' dependency. Install it via `pip install pyarrow`."
        ) from exc

    if runs_path:
        targets.append(
            _write_parquet_table(summary.get("runs", []), Path(runs_path), _RUN_PARQUET_SCHEMA, pa, pq)
        )
    if daily_path:
        targets.append(
            _write_parquet_table(summary.get("daily_metrics", []), Path(daily_path), _DAILY_PARQUET_SCHEMA, pa, pq)
        )
    return targets


def ingest_search_history(
    log_path: Path | str = DEFAULT_LOG_PATH,
    output_path: Path | str = DEFAULT_SUMMARY_PATH,
    *,
    preset_tags_path: Path | str | None = None,
    lookback: int = 50,
    runs_parquet_path: Path | str | None = None,
    daily_parquet_path: Path | str | None = None,
    emit_tail_log: bool = True,
) -> dict[str, Any]:
    log = Path(log_path)
    runs = _build_runs_from_log(log)
    summary = _build_summary(
        runs,
        log_path=log,
        preset_tags_path=Path(preset_tags_path) if preset_tags_path else None,
        lookback=lookback,
    )
    write_summary(summary, output_path)
    _write_parquet_tables(
        summary,
        runs_path=Path(runs_parquet_path) if runs_parquet_path else None,
        daily_path=Path(daily_parquet_path) if daily_parquet_path else None,
    )
    if emit_tail_log:
        _log_summary(summary, action="search-ledger ingest")
    return summary


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
    runs = _build_runs_from_sqlite(Path(db_path))
    summary = _build_summary(
        runs,
        log_path=Path(db_path),
        preset_tags_path=Path(preset_tags_path) if preset_tags_path else None,
        lookback=lookback,
    )
    write_summary(summary, output_path)
    _write_parquet_tables(
        summary,
        runs_path=Path(runs_parquet_path) if runs_parquet_path else None,
        daily_path=Path(daily_parquet_path) if daily_parquet_path else None,
    )
    if emit_tail_log:
        _log_summary(summary, action="search-ledger migrate")
    return summary


def compute_preset_drift_from_summary(
    summary_path: Path | str = DEFAULT_SUMMARY_PATH,
    *,
    lookback: int = 50,
    preset_tags_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    summary = read_summary(summary_path)
    runs_payload = summary.get("runs", [])
    runs: list[RunRecord] = []
    if isinstance(runs_payload, list):
        for entry in runs_payload:
            if isinstance(entry, dict):
                runs.append(_record_from_summary(entry))
    preset_tags = _load_preset_tags(Path(preset_tags_path) if preset_tags_path else None)
    return _compute_preset_drift(runs, lookback=lookback, preset_tags=preset_tags)


def _render_stats(summary: dict[str, Any], *, limit: int = 10) -> None:
    if not summary:
        print("No telemetry summary found. Run the ingest command first.")
        return
    print(f"Total runs: {summary.get('total_runs', 0)}")
    print(f"Runs with matches: {summary.get('runs_with_matches', 0)}")
    print(f"Runs (last 24h): {summary.get('runs_last_24h', 0)}")
    print(f"Avg duration (ms): {summary.get('avg_duration_ms')}\n")
    print("Top patterns:")
    for entry in summary.get("top_patterns", [])[:limit]:
        print(
            f"  - {entry['pattern']}: {entry['runs']} runs, {entry['total_matches']} matches (avg files {entry['avg_files_scanned']:.1f})"
        )
    print("\nPreset drift:")
    for entry in summary.get("preset_drift", [])[:limit]:
        print(
            f"  - {entry['preset']}: {entry['status']} (Δmatch {entry['delta_match_rate']}, Δdensity {entry['delta_density']})"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search telemetry ledger commands")
    parser.add_argument("--no-tail-log", action="store_true", help="Disable tail log emission")
    subparsers = parser.add_subparsers(dest="command", required=False)

    ingest_parser = subparsers.add_parser("ingest", help="Recompute ledger from JSONL log")
    ingest_parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    ingest_parser.add_argument("--output", type=Path, default=DEFAULT_SUMMARY_PATH)
    ingest_parser.add_argument("--preset-tags", type=Path, default=None)
    ingest_parser.add_argument("--lookback", type=int, default=50)
    ingest_parser.add_argument("--runs-parquet", type=Path, default=None, help="Optional Parquet path for run-level entries")
    ingest_parser.add_argument(
        "--daily-parquet",
        type=Path,
        default=None,
        help="Optional Parquet path for aggregated daily metrics",
    )

    migrate_parser = subparsers.add_parser(
        "migrate-from-sqlite", help="One-shot helper to migrate the legacy SQLite DB into JSON"
    )
    migrate_parser.add_argument("--db-path", type=Path, required=True)
    migrate_parser.add_argument("--output", type=Path, default=DEFAULT_SUMMARY_PATH)
    migrate_parser.add_argument("--preset-tags", type=Path, default=None)
    migrate_parser.add_argument("--lookback", type=int, default=50)
    migrate_parser.add_argument("--runs-parquet", type=Path, default=None)
    migrate_parser.add_argument("--daily-parquet", type=Path, default=None)

    stats_parser = subparsers.add_parser("stats", help="Print ledger summary details")
    stats_parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    stats_parser.add_argument("--limit", type=int, default=5)

    parser.set_defaults(command="ingest")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    tail_log_enabled = not getattr(args, "no_tail_log", False)

    if args.command == "stats":
        summary = read_summary(args.summary_path)
        _render_stats(summary, limit=args.limit)
        return 0
    if args.command == "migrate-from-sqlite":
        migrate_from_sqlite(
            args.db_path,
            output_path=args.output,
            preset_tags_path=args.preset_tags,
            lookback=args.lookback,
            runs_parquet_path=args.runs_parquet,
            daily_parquet_path=args.daily_parquet,
            emit_tail_log=tail_log_enabled,
        )
        print(f"Ledger written to {args.output}")
        return 0

    ingest_search_history(
        log_path=args.log_path,
        output_path=args.output,
        preset_tags_path=args.preset_tags,
        lookback=args.lookback,
        runs_parquet_path=args.runs_parquet,
        daily_parquet_path=args.daily_parquet,
        emit_tail_log=tail_log_enabled,
    )
    print(f"Ledger written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
