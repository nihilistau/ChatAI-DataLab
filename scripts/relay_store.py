#!/usr/bin/env python
"""CLI helpers for inspecting and mutating the Relay data store."""

from __future__ import annotations

import argparse
from collections import deque
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from textwrap import shorten
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("LAB_ROOT", str(REPO_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relay.backend.app.config import get_settings
from relay.backend.app.schemas import ArtifactCreate, TailLogEntryCreate
from relay.backend.app.services.data_store import data_store_context
from scripts.ops_telemetry import telemetry_span


TELEMETRY_SKIP_KEYS = {
    "skip_tail_log",
    "skip_release_log",
    "tail_log_source",
    "release_log_kind",
    "release_log_path",
    "func",
}


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _coerce_arg(value: Any) -> Any:
    if isinstance(value, Path):
        return _relativize(value)
    if isinstance(value, list):
        return [_coerce_arg(item) for item in value]
    return value


def _sanitize_args(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in vars(args).items():
        if key in TELEMETRY_SKIP_KEYS:
            continue
        payload[key] = _coerce_arg(value)
    return payload


# -----------------------------------------------------------------------------
# Serialization helpers
# -----------------------------------------------------------------------------

def _isoformat(value):
    if isinstance(value, str):
        return value
    return value.isoformat()


def _interaction_to_dict(record) -> dict[str, Any]:
    payload = asdict(record)
    payload["created_at"] = _isoformat(record.created_at)
    return payload


def _artifact_to_dict(record) -> dict[str, Any]:
    payload = asdict(record)
    payload["created_at"] = _isoformat(record.created_at)
    payload["updated_at"] = _isoformat(record.updated_at)
    return payload


def _tail_log_to_dict(record) -> dict[str, Any]:
    payload = asdict(record)
    payload["created_at"] = _isoformat(record.created_at)
    return payload


# -----------------------------------------------------------------------------
# Command implementations
# -----------------------------------------------------------------------------

def cmd_interactions(args: argparse.Namespace) -> dict[str, Any]:
    with data_store_context() as store:
        records = store.list_interactions(limit=args.limit)
    if args.json:
        print(json.dumps([_interaction_to_dict(item) for item in records], indent=2))
        return {"count": len(records), "json": True}
    for record in records:
        prompt = shorten(record.user_prompt_text, width=80, placeholder=" …")
        print(f"{record.created_at.isoformat()} · {record.model_name:<12} · {prompt}")
    return {"count": len(records), "json": False}


def cmd_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    with data_store_context() as store:
        records = store.list_artifacts(limit=args.limit)
    if args.json:
        print(json.dumps([_artifact_to_dict(item) for item in records], indent=2))
        return {"count": len(records), "json": True}
    for record in records:
        body_preview = shorten(record.body, width=80, placeholder=" …")
        print(f"{record.updated_at.isoformat()} · {record.title} · {body_preview}")
    return {"count": len(records), "json": False}


def cmd_create_artifact(args: argparse.Namespace) -> dict[str, Any]:
    payload = ArtifactCreate(
        title=args.title,
        body=args.body,
        owner=args.owner,
        category=args.category,
        accent=args.accent,
    )
    with data_store_context() as store:
        record = store.create_artifact(payload)
    data = _artifact_to_dict(record)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Created artifact {record.id} for {record.owner} · {record.title}")
    return {"artifact_id": str(record.id), "owner": record.owner}


def _format_tail_entry(entry) -> str:
    message = shorten(entry.message, width=90, placeholder=" …")
    return f"{entry.created_at.isoformat()} · {entry.source:<10} · {message}"


def cmd_tail_log(args: argparse.Namespace) -> dict[str, Any]:
    def _emit(entries):
        payload = [_tail_log_to_dict(item) for item in entries]
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            for entry in entries:
                print(_format_tail_entry(entry), flush=True)

    if args.follow and args.json:
        raise SystemExit("--follow cannot be combined with --json")

    if args.follow:
        buffer_size = max(args.limit * 4, 50)
        seen_order = deque(maxlen=buffer_size)
        seen = set()
        try:
            while True:
                with data_store_context() as store:
                    entries = store.list_tail_log(limit=args.limit)
                for entry in reversed(entries):
                    if entry.id in seen:
                        continue
                    print(_format_tail_entry(entry), flush=True)
                    seen.add(entry.id)
                    seen_order.append(entry.id)
                while len(seen) > len(seen_order):
                    expired = seen_order.popleft()
                    seen.discard(expired)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return {"follow": True, "limit": args.limit, "interval": args.interval}
    else:
        with data_store_context() as store:
            entries = store.list_tail_log(limit=args.limit)
        _emit(entries)
        return {"count": len(entries), "json": args.json, "follow": False}


def cmd_tail_log_add(args: argparse.Namespace) -> dict[str, Any]:
    payload = TailLogEntryCreate(message=args.message, source=args.source)
    with data_store_context() as store:
        entry = store.create_tail_log_entry(payload)
    data = _tail_log_to_dict(entry)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Logged '{entry.message}' from {entry.source}")
    return {"entry_id": str(entry.id), "source": entry.source}


def cmd_summary(_: argparse.Namespace) -> dict[str, Any]:
    with data_store_context() as store:
        interactions = store.count_interactions()
        artifacts = len(store.list_artifacts(limit=1))
        tail_log = len(store.list_tail_log(limit=1))
    settings = get_settings()
    summary = {
        "provider": settings.database_provider,
        "interaction_count": interactions,
        "artifact_count_sample": artifacts,
        "tail_log_sample": tail_log,
    }
    print(json.dumps(summary, indent=2))
    return summary


# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Relay data store utility")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="relay-store", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="relay_store", help="Release log kind label")
    parser.add_argument("--release-log-path", default=None, help="Optional release log override path")
    sub = parser.add_subparsers(dest="command", required=True)

    interactions_cmd = sub.add_parser("interactions", help="List recent chat interactions")
    interactions_cmd.add_argument("--limit", type=int, default=20, help="Maximum records to return")
    interactions_cmd.add_argument("--json", action="store_true", help="Emit JSON output")
    interactions_cmd.set_defaults(func=cmd_interactions)

    artifacts_cmd = sub.add_parser("artifacts", help="List stored artifacts")
    artifacts_cmd.add_argument("--limit", type=int, default=12, help="Maximum records to return")
    artifacts_cmd.add_argument("--json", action="store_true", help="Emit JSON output")
    artifacts_cmd.set_defaults(func=cmd_artifacts)

    create_artifact_cmd = sub.add_parser("create-artifact", help="Insert a new artifact")
    create_artifact_cmd.add_argument("--title", required=True)
    create_artifact_cmd.add_argument("--body", required=True)
    create_artifact_cmd.add_argument("--owner", default="ops-bot")
    create_artifact_cmd.add_argument("--category", default="artifact")
    create_artifact_cmd.add_argument("--accent", default=None)
    create_artifact_cmd.add_argument("--json", action="store_true", help="Emit JSON output")
    create_artifact_cmd.set_defaults(func=cmd_create_artifact)

    tail_log_cmd = sub.add_parser("tail-log", help="List tail log entries")
    tail_log_cmd.add_argument("--limit", type=int, default=20)
    tail_log_cmd.add_argument("--json", action="store_true")
    tail_log_cmd.add_argument(
        "--follow",
        action="store_true",
        help="Continuously poll for new entries and stream them to stdout",
    )
    tail_log_cmd.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds when using --follow",
    )
    tail_log_cmd.set_defaults(func=cmd_tail_log)

    tail_log_add_cmd = sub.add_parser("tail-log-add", help="Append a tail log entry")
    tail_log_add_cmd.add_argument("message")
    tail_log_add_cmd.add_argument("--source", default="cli")
    tail_log_add_cmd.add_argument("--json", action="store_true")
    tail_log_add_cmd.set_defaults(func=cmd_tail_log_add)

    summary_cmd = sub.add_parser("summary", help="Show provider + basic counts")
    summary_cmd.set_defaults(func=cmd_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    sanitized_args = _sanitize_args(args)
    status_holder = {"state": "pending"}

    def _tail_message() -> str:
        return f"relay_store {args.command} {status_holder['state']}"

    release_entry = {
        "kind": "relay_store",
        "command": args.command,
        "args": sanitized_args,
    }
    release_details = {"args": sanitized_args}

    with telemetry_span(
        f"relay-store-{args.command}",
        component="relay_store",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary=f"relay_store {args.command}",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as recorder:
        try:
            details = args.func(args) or {}
        except Exception as exc:
            status_holder["state"] = "failed"
            recorder.record_step(args.command, status="failed", details={"error": str(exc)})
            release_entry["error"] = str(exc)
            recorder.set_metadata(command=args.command, status="failed")
            raise
        status_holder["state"] = "ok"
        recorder.record_step(args.command, status="ok", details=details or sanitized_args)
        recorder.set_metadata(command=args.command, status="ok")
        release_entry["details"] = details or sanitized_args
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
