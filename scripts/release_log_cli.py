#!/usr/bin/env python3
"""Headless reader for data/logs/release.log with filtering helpers."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relay.backend.app.services.release_log import list_release_log_entries
from scripts.ops_telemetry import telemetry_span

DEFAULT_LIMIT = 12
ISO_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S")


def _parse_iso(timestamp: str | None) -> str:
    if not timestamp:
        return "unknown"
    try:
        return datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        for fmt in ISO_FORMATS:
            try:
                return datetime.strptime(timestamp, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
    return timestamp


def _matches(entry: dict[str, Any], args: argparse.Namespace) -> bool:
    status = (entry.get("status") or "ok").lower()
    kind = (entry.get("kind") or "release_pipeline").lower()
    source = (entry.get("source") or "").lower()
    if args.status and status not in args.status:
        return False
    if args.kind and kind not in args.kind:
        return False
    if args.source and source not in args.source:
        return False
    if args.search:
        haystack = json.dumps(entry, default=str).lower()
        if args.search.lower() not in haystack:
            return False
    return True


def _normalize_filters(values: Sequence[str]) -> list[str]:
    return sorted({value.lower() for value in values})


def _load_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    raw_entries = list_release_log_entries(args.limit)
    filtered: list[dict[str, Any]] = []
    for entry in raw_entries:
        if _matches(entry, args):
            filtered.append(entry)
    return filtered


def _print_entry(entry: dict[str, Any], args: argparse.Namespace) -> None:
    timestamp = _parse_iso(entry.get("timestamp"))
    status = (entry.get("status") or "ok").upper()
    title = entry.get("tag") or entry.get("release_tag") or entry.get("action") or entry.get("kind")
    summary = entry.get("summary") or entry.get("notes") or ""
    branch = entry.get("branch") or entry.get("release_branch")
    commit = entry.get("commit")
    duration = entry.get("duration_seconds")
    source = entry.get("source")
    lines = [
        f"[{status:<7}] {timestamp} · {entry.get('kind', 'release_pipeline')} · {title}",
    ]
    chips: list[str] = []
    if branch:
        chips.append(f"branch={branch}")
    if commit:
        chips.append(f"commit={commit[:8]}")
    if source:
        chips.append(f"source={source}")
    if entry.get("release_mode"):
        chips.append(f"mode={entry['release_mode']}")
    if entry.get("release_tag") and entry.get("release_tag") != title:
        chips.append(f"release_tag={entry['release_tag']}")
    if entry.get("checkpoint_tag"):
        chips.append(f"checkpoint={entry['checkpoint_tag']}")
    if entry.get("goal_milestone"):
        chips.append(f"milestone={entry['goal_milestone']}")
    if duration is not None:
        chips.append(f"duration={duration:.1f}s")
    if chips:
        lines.append("    " + " | ".join(chips))
    if summary:
        lines.append(f"    summary: {summary}")
    if entry.get("error"):
        lines.append(f"    error: {entry['error']}")
    if args.show_details and entry.get("details"):
        details = json.dumps(entry["details"], indent=2, ensure_ascii=False)
        lines.append("    details:\n" + "\n".join(f"        {line}" for line in details.splitlines()))
    if args.show_metadata and entry.get("metadata"):
        metadata = json.dumps(entry["metadata"], indent=2, ensure_ascii=False)
        lines.append("    metadata:\n" + "\n".join(f"        {line}" for line in metadata.splitlines()))
    if args.show_timeline and entry.get("timeline"):
        lines.append("    timeline:")
        for step in entry["timeline"]:
            step_status = (step.get("status") or "unknown").upper()
            step_name = step.get("name") or "step"
            step_details = step.get("details")
            duration_txt = ""
            if step.get("duration_seconds") is not None:
                duration_txt = f" ({step['duration_seconds']:.2f}s)"
            detail_txt = f" — {step_details}" if step_details else ""
            lines.append(f"        [{step_status:<7}] {step_name}{duration_txt}{detail_txt}")
    print("\n".join(lines))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Headless release log inspector")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max entries to load (newest first)")
    parser.add_argument("--status", action="append", default=[], help="Filter by status (repeatable)")
    parser.add_argument("--kind", action="append", default=[], help="Filter by kind (repeatable)")
    parser.add_argument("--source", action="append", default=[], help="Filter by source label (repeatable)")
    parser.add_argument("--search", help="Case-insensitive substring search across entries")
    parser.add_argument("--json", action="store_true", help="Emit filtered entries as JSON and exit")
    parser.add_argument("--show-timeline", action="store_true", help="Include timeline steps in text output")
    parser.add_argument("--show-details", action="store_true", help="Include 'details' payloads in text output")
    parser.add_argument("--show-metadata", action="store_true", help="Include metadata payloads in text output")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable the telemetry tail log event for this command")
    parser.add_argument("--tail-log-source", default="release-log-cli", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="release_log_cli", help="Kind label for telemetry release entries")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.status = _normalize_filters(args.status)
    args.kind = _normalize_filters(args.kind)
    args.source = _normalize_filters(args.source)

    with telemetry_span(
        action="inspect",
        component="release_log_cli",
        tail_source=args.tail_log_source,
        release_kind=args.release_log_kind,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=True,
        release_summary=f"limit={args.limit} json={args.json}",
    ):
        entries = _load_entries(args)
        if args.json:
            json.dump(entries, sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
        if not entries:
            print("No release log entries matched your filters.")
            return 0
        for entry in entries:
            _print_entry(entry, args)
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
