#!/usr/bin/env python3
"""Helper CLI for the optional /changes Master Change history system.

This tool is strictly for generating/browsing narrative reports and does not
participate in release or integrity automation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS_DIR = ROOT / "changes" / "records"
DEFAULT_TEMPLATE = ROOT / "changes" / "templates" / "master_change_template.md"

from scripts.ops_telemetry import telemetry_span


TELEMETRY_SKIP_KEYS = {
    "skip_tail_log",
    "skip_release_log",
    "tail_log_source",
    "release_log_kind",
    "release_log_path",
}


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
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


@dataclass
class ChangeRecord:
    master_id: str
    title: str
    status: str
    started: str | None
    completed: str | None
    version: str | None
    owner: str | None
    tags: list[str]
    runs: list[str]
    related: str | None
    path: Path

    @property
    def summary_line(self) -> str:
        tag_str = ", ".join(self.tags) if self.tags else "-"
        status = self.status or "unknown"
        return f"{self.master_id:<20} {status:<10} {self.title} [{tag_str}]"


def _find_meta_block(text: str) -> str:
    start = text.find("<!--")
    if start == -1:
        raise ValueError("Missing opening '<!--' metadata block")
    end = text.find("-->", start + 4)
    if end == -1:
        raise ValueError("Missing closing '-->' metadata block")
    return text[start + 4 : end].strip()


def load_record(path: Path) -> ChangeRecord:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Unable to read record {path}") from exc
    meta_block = _find_meta_block(text)
    try:
        payload = json.loads(meta_block)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata JSON malformed in {path}: {exc}") from exc
    return ChangeRecord(
        master_id=payload.get("master_id") or path.stem,
        title=payload.get("title", "(untitled)"),
        status=payload.get("status", "unknown"),
        started=payload.get("started"),
        completed=payload.get("completed"),
        version=payload.get("version"),
        owner=payload.get("owner"),
        tags=list(payload.get("tags", [])),
        runs=list(payload.get("change_runs", [])),
        related=payload.get("related_master"),
        path=path,
    )


def iter_records(records_dir: Path) -> Iterable[ChangeRecord]:
    if not records_dir.exists():
        return []
    files = sorted(records_dir.glob("*.md"))
    for file_path in files:
        try:
            yield load_record(file_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Warning: unable to parse {file_path}: {exc}", file=sys.stderr)


def cmd_list(records_dir: Path) -> int:
    entries = list(iter_records(records_dir))
    if not entries:
        print("No change records found.")
        return 0
    header = f"{'Master ID':<20} {'Status':<10} Title [tags]"
    print(header)
    print("-" * len(header))
    for record in entries:
        print(record.summary_line)
    return 0


def cmd_show(records_dir: Path, master_id: str) -> int:
    for record in iter_records(records_dir):
        if record.master_id.lower() == master_id.lower():
            print(f"Master ID: {record.master_id}")
            print(f"Title: {record.title}")
            print(f"Status: {record.status}")
            if record.owner:
                print(f"Owner: {record.owner}")
            if record.started or record.completed:
                print(f"Timeline: {record.started or '?'} → {record.completed or '?'}")
            if record.version:
                print(f"Version: {record.version}")
            if record.tags:
                print(f"Tags: {', '.join(record.tags)}")
            if record.runs:
                print("Change runs:")
                for run in record.runs:
                    print(f"  - {run}")
            if record.related:
                print(f"Related Master: {record.related}")
            print(f"Path: {record.path.relative_to(ROOT)}")
            body_hint = record.path.read_text(encoding="utf-8").split("-->", 1)[-1].strip()
            preview = "\n".join(body_hint.splitlines()[:20])
            print("\n--- Preview ---\n")
            print(preview)
            return 0
    print(f"No record matching {master_id}")
    return 1


def _auto_master_id() -> str:
    return datetime.now(timezone.utc).strftime("MC-%Y-%m-%d-%H%M%S")


def _default_run_example(master_id: str) -> str:
    suffix = master_id.replace("MC-", "CR-")
    return f"{suffix}A"


def _serialize_list(values: Sequence[str]) -> str:
    cleaned = [v.strip() for v in values if v.strip()]
    return ", ".join(f'"{value}"' for value in cleaned)


def _human_list(values: Sequence[str]) -> str:
    cleaned = [v.strip() for v in values if v.strip()]
    return ", ".join(cleaned) if cleaned else "-"


def cmd_new(
    records_dir: Path,
    template_path: Path,
    title: str,
    tags: list[str],
    owner: str,
    status: str,
    version: str,
    started: str,
    completed: str,
    runs: list[str],
    related: str | None,
    intent: str,
    fit: str,
    validation_plan: str,
    risks: str,
    master_id: str | None,
) -> int:
    master_id = master_id or _auto_master_id()
    target_path = records_dir / f"{master_id}.md"
    if target_path.exists():
        raise FileExistsError(f"Record {target_path} already exists")

    template_text = template_path.read_text(encoding="utf-8")
    related_json = f'"{related}"' if related else "null"
    runs_for_meta = runs or []
    tags_for_meta = tags or []

    context = {
        "MASTER_ID": master_id,
        "TITLE": title,
        "STATUS": status,
        "OWNER": owner,
        "VERSION": version,
        "STARTED": started,
        "COMPLETED": completed,
        "TAGS": _serialize_list(tags_for_meta),
        "RUN_IDS": _serialize_list(runs_for_meta),
        "RELATED": related_json,
        "TAGS_HUMAN": _human_list(tags_for_meta),
        "RELATED_HUMAN": related or "None",
        "INTENT": intent,
        "FIT": fit,
        "VALIDATION_PLAN": validation_plan,
        "RISKS": risks,
        "RUN_EXAMPLE_ID": runs_for_meta[0] if runs_for_meta else _default_run_example(master_id),
        "RUN_EXAMPLE_TITLE": "Describe change run focus",
        "RUN_EXAMPLE_TIME": started or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    rendered = template_text.format(**context)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(rendered, encoding="utf-8")
    print(f"Created {target_path.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Change Run history helper")
    parser.add_argument("--records-dir", default=str(DEFAULT_RECORDS_DIR), help="Directory containing master change records")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Template used when creating new records")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="change-runs", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="change_runs", help="Release log kind label")
    parser.add_argument("--release-log-path", default=None, help="Optional release log override path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List master change records")

    show_parser = subparsers.add_parser("show", help="Show metadata for a master change")
    show_parser.add_argument("master_id")

    new_parser = subparsers.add_parser("new", help="Create a new master change record from the template")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--tags", default="", help="Comma-separated tags")
    new_parser.add_argument("--owner", default="copilot")
    new_parser.add_argument("--status", default="draft")
    new_parser.add_argument("--version", default="0.1")
    new_parser.add_argument("--started", default=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    new_parser.add_argument("--completed", default="")
    new_parser.add_argument("--runs", default="", help="Comma-separated change run ids")
    new_parser.add_argument("--related", help="Related master id, if any")
    new_parser.add_argument("--master-id", help="Explicit master change id (defaults to MC-<timestamp>)")
    new_parser.add_argument("--intent", default="Document the core objective.")
    new_parser.add_argument("--fit", default="Explain how this change fits the roadmap.")
    new_parser.add_argument("--validation-plan", default="List planned tests or guardrails.")
    new_parser.add_argument("--risks", default="Call out risks + mitigations.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.records_dir = Path(args.records_dir).expanduser().resolve()
    if getattr(args, "template", None):
        args.template = Path(args.template).expanduser().resolve()

    sanitized_args = _sanitize_args(args)
    status_holder: dict[str, int | None] = {"exit_code": None}

    def _tail_message() -> str:
        exit_code = status_holder["exit_code"]
        if exit_code is None:
            return f"change_runs {args.command} pending"
        status = "ok" if exit_code == 0 else f"exit={exit_code}"
        return f"change_runs {args.command} {status}"

    release_entry = {
        "kind": "change_runs",
        "command": args.command,
        "args": sanitized_args,
    }
    release_details = {"args": sanitized_args}

    def _run_selected_command() -> int:
        if args.command == "list":
            return cmd_list(args.records_dir)
        if args.command == "show":
            return cmd_show(args.records_dir, args.master_id)
        if args.command == "new":
            tags = [t.strip() for t in args.tags.split(",") if t.strip()]
            runs = [r.strip() for r in args.runs.split(",") if r.strip()]
            return cmd_new(
                records_dir=args.records_dir,
                template_path=args.template,
                title=args.title,
                tags=tags,
                owner=args.owner,
                status=args.status,
                version=args.version,
                started=args.started,
                completed=args.completed,
                runs=runs,
                related=args.related,
                intent=args.intent,
                fit=args.fit,
                validation_plan=args.validation_plan,
                risks=args.risks,
                master_id=args.master_id,
            )
        parser.error("Unknown command")
        return 1

    with telemetry_span(
        f"change-runs-{args.command}",
        component="change_runs",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary=f"change_runs {args.command}",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as recorder:
        try:
            exit_code = _run_selected_command()
        except Exception as exc:
            status_holder["exit_code"] = 1
            recorder.record_step(args.command, status="failed", details={"error": str(exc)})
            release_entry["error"] = str(exc)
            recorder.set_metadata(command=args.command, status="failed")
            raise
        status_holder["exit_code"] = exit_code
        recorder.record_step(
            args.command,
            status="ok" if exit_code == 0 else "failed",
            details=release_details["args"],
        )
        recorder.set_metadata(command=args.command, exit_code=exit_code)
        release_entry["exit_code"] = exit_code
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
