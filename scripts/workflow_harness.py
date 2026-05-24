#!/usr/bin/env python3
"""Ops harness that chains release, docs, rebrand, and change logging steps."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
DOCS_DIR = ROOT / "docs"
GOALS_FILE = DOCS_DIR / "GOALS_AND_ACHIEVEMENTS.md"
CHANGE_TEMPLATE = ROOT / "changes" / "templates" / "master_change_template.md"
CHANGE_RECORDS = ROOT / "changes" / "records"
PYTHON = sys.executable
RELEASE_LOG_PATH = ROOT / "data" / "logs" / "release.log"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_telemetry import TelemetryRecorder, telemetry_span


class HarnessError(RuntimeError):
    """Base error for workflow harness failures."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat(timespec="seconds")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialize_args(args: argparse.Namespace) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            snapshot[key] = str(value)
        elif isinstance(value, (list, tuple)):
            serialized: list[Any] = []
            for item in value:
                serialized.append(str(item) if isinstance(item, Path) else item)
            snapshot[key] = serialized
        else:
            snapshot[key] = value
    return snapshot


def _build_timeline_summary(args: argparse.Namespace, timeline: list[dict[str, Any]]) -> dict[str, Any]:
    started_at = timeline[0]["started_at"] if timeline else None
    ended_at = timeline[-1]["ended_at"] if timeline else None
    summary: dict[str, Any] = {
        "generated_at": _iso_now(),
        "started_at": started_at,
        "ended_at": ended_at,
        "notes": args.notes,
        "release_mode": args.release_mode,
        "timeline": timeline,
        "options": _serialize_args(args),
    }
    if started_at and ended_at:
        try:
            start_dt = datetime.fromisoformat(started_at)
            end_dt = datetime.fromisoformat(ended_at)
            summary["duration_seconds"] = round((end_dt - start_dt).total_seconds(), 3)
        except ValueError:
            pass
    return summary


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload))
        handle.write("\n")


def _default_tail_log_message(summary: dict[str, Any], args: argparse.Namespace) -> str:
    options = summary.get("options", {})
    timeline_target = options.get("timeline_json") or options.get("timeline_jsonl") or "n/a"
    release_state = "skipped" if getattr(args, "skip_release", False) else "enabled"
    return (
        f"workflow harness completed · release_mode={args.release_mode} "
        f"· release_step={release_state} · timeline={timeline_target}"
    )


def _initial_release_entry(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "kind": "workflow_harness",
        "action": "workflow_harness",
        "release_mode": args.release_mode,
        "release_tag": args.release_tag,
        "goal_milestone": args.goal_milestone,
        "change_master_id": args.change_master_id,
        "checkpoint_tag": args.checkpoint_tag,
        "notes": args.notes,
    }


def _run(command: Sequence[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    readable = " ".join(command)
    print(f"→ {readable}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(
        command,
        cwd=cwd or ROOT,
        text=True,
        capture_output=capture,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        stdout = result.stdout if capture else "<streamed>"
        stderr = result.stderr if capture else "<streamed>"
        raise HarnessError(
            f"Command failed (exit code {result.returncode}): {readable}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    return result


def _update_goals_file(*, milestone: str, summary: str, artifacts: str, date_str: str, milestone_label: str) -> str:
    if not GOALS_FILE.exists():
        raise HarnessError(f"Goals file missing: {GOALS_FILE}")
    text = GOALS_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    timestamp = _utc_now().strftime("%Y-%m-%d %H:%M UTC")
    last_updated_prefix = "> **Last updated:**"
    milestone_prefix = "> **Current milestone:**"
    updated = False

    for idx, line in enumerate(lines):
        if line.startswith(last_updated_prefix):
            lines[idx] = f"{last_updated_prefix} {timestamp}  "
            updated = True
        if line.startswith(milestone_prefix):
            lines[idx] = f"{milestone_prefix} {milestone_label}  "
    if not updated:
        raise HarnessError("Unable to locate 'Last updated' marker in goals file")

    row = f"| {date_str} | {milestone} | {summary} | {artifacts} |"
    if row in text:
        GOALS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "Goals file already contained milestone; timestamps updated"

    table_header = "| Date (UTC) | Milestone | Summary | Primary Artifacts |"
    try:
        header_index = lines.index(table_header)
    except ValueError as exc:
        raise HarnessError("Unable to find Completed Milestones table header") from exc
    divider_index = header_index + 1
    lines.insert(divider_index + 1, row)
    GOALS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"Inserted milestone row for {milestone}"


def _create_change_record(
    *,
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
    validation: str,
    risks: str,
    master_id: str | None,
) -> str:
    from scripts import change_runs  # type: ignore

    before = {path for path in CHANGE_RECORDS.glob("*.md")}
    result = change_runs.cmd_new(
        records_dir=CHANGE_RECORDS,
        template_path=CHANGE_TEMPLATE,
        title=title,
        tags=tags,
        owner=owner,
        status=status,
        version=version,
        started=started,
        completed=completed,
        runs=runs,
        related=related,
        intent=intent,
        fit=fit,
        validation_plan=validation,
        risks=risks,
        master_id=master_id,
    )
    if result != 0:
        raise HarnessError("Failed to create change record")
    after = {path for path in CHANGE_RECORDS.glob("*.md")}
    new_files = sorted(after - before)
    if new_files:
        created = new_files[-1]
    elif after:
        created = max(after)
    else:  # pragma: no cover - defensive
        raise HarnessError("Change record creation succeeded but file not found")
    return f"Created {created.relative_to(ROOT)}"


def _run_release_pipeline(args: argparse.Namespace) -> str:
    tag = args.release_tag or _utc_now().strftime("v%Y%m%d-%H%M%S-automation")
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "release_pipeline.py"),
        "--tag",
        tag,
        "--notes",
        args.notes or "workflow harness",
    ]
    if args.release_branch:
        cmd.extend(["--branch", args.release_branch])
    if args.release_mode == "dry-run":
        cmd.append("--dry-run")
        cmd.append("--allow-dirty")
        cmd.append("--no-push")
    elif not args.release_push:
        cmd.append("--no-push")
    if args.release_skip_tests:
        cmd.append("--skip-tests")
    if args.release_skip_integrity:
        cmd.append("--skip-integrity")
    if args.release_no_autofix:
        cmd.append("--no-auto-fix")
    if args.release_allow_dirty and "--allow-dirty" not in cmd:
        cmd.append("--allow-dirty")
    if args.release_force_artifacts:
        cmd.append("--force-release-dir")
    result = _run(cmd)
    return f"Release pipeline finished (tag {tag})"


def _run_rebrand(args: argparse.Namespace) -> str:
    from scripts import rebrand_reset  # type: ignore

    argv: list[str] = []
    if args.rebrand_config:
        argv.extend(["--config", args.rebrand_config])
    if args.rebrand_steps:
        argv.extend(["--steps", *args.rebrand_steps])
    if not args.rebrand_apply:
        argv.append("--dry-run")
    if args.rebrand_list:
        argv.append("--list")
    rebrand_reset.main(argv)
    mode = "apply" if args.rebrand_apply else "dry-run"
    return f"Rebrand workflow ({mode}) completed"


def _checkpoint_integrity(tag: str, reason: str | None) -> str:
    reason = reason or f"workflow harness checkpoint {tag}"
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "project_integrity.py"),
        "checkpoint",
        "--tag",
        tag,
        "--reason",
        reason,
    ]
    result = _run(cmd)
    return "Checkpoint created"


def _run_integrity_status() -> str:
    cmd = [PYTHON, str(SCRIPTS_DIR / "project_integrity.py"), "status"]
    result = _run(cmd)
    return "Integrity status captured"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Composite workflow harness for release + docs + change logging")
    parser.add_argument("--notes", default="Automation harness run", help="Context string passed to release artifacts")

    # Release options
    parser.add_argument("--release-tag", help="Override release tag for pipeline step")
    parser.add_argument("--release-branch", help="Expected branch for release pipeline")
    parser.add_argument("--release-mode", choices=["dry-run", "full"], default="dry-run")
    parser.add_argument("--release-skip-tests", action="store_true", help="Skip npm + pytest when invoking release pipeline")
    parser.add_argument("--release-skip-integrity", action="store_true", help="Skip integrity guardrail in release pipeline")
    parser.add_argument("--release-no-autofix", action="store_true", help="Disable eslint autofix retries")
    parser.add_argument("--release-allow-dirty", action="store_true", help="Allow dirty worktree for release pipeline")
    parser.add_argument("--release-force-artifacts", action="store_true", help="Overwrite release artifact directory")
    parser.add_argument("--release-push", action="store_true", help="Push branch + tag when release pipeline succeeds")

    # Docs / goals options
    parser.add_argument("--goal-milestone", default="Ops workflow harness", help="Milestone label for goals log")
    parser.add_argument("--goal-summary", default="Scripted release + docs automation harness.", help="Summary for goals log")
    parser.add_argument(
        "--goal-artifacts",
        default="`scripts/workflow_harness.py`, `scripts/control_center.py`, `data/commands.json`, `docs/AGENT_OPERATIONS.md`",
        help="Artifacts column for goals log",
    )
    parser.add_argument("--goal-date", help="Date string for goals table (defaults to today)")
    parser.add_argument("--goal-current-label", default="Automation harness baseline", help="Current milestone label to stamp at top")

    # Change record options
    parser.add_argument("--change-title", default="Ops automation harness", help="Master change title")
    parser.add_argument("--change-tags", default="release,automation,docs", help="Comma-separated tags")
    parser.add_argument("--change-owner", default="copilot")
    parser.add_argument("--change-status", default="complete")
    parser.add_argument("--change-version", default="1.0")
    parser.add_argument("--change-started")
    parser.add_argument("--change-completed")
    parser.add_argument("--change-runs", default="")
    parser.add_argument("--change-related")
    parser.add_argument("--change-master-id")
    parser.add_argument("--change-intent", default="Bundle release, docs, and rebrand workflows so Ops can fire one command.")
    parser.add_argument(
        "--change-fit",
        default="Automates the user's requested freeze → docs → change record → rebrand loop, keeping guardrails consistent.",
    )
    parser.add_argument(
        "--change-validation",
        default="Release pipeline dry-run + integrity status + rebrand dry-run",
    )
    parser.add_argument("--change-risks", default="Low risk; script composes existing, battle-tested tooling.")

    # Rebrand options
    parser.add_argument("--rebrand-config", help="Optional config override for rebrand workflow")
    parser.add_argument("--rebrand-steps", nargs="*", choices=["renames", "copies", "replacements", "commands"], help="Limit rebrand steps")
    parser.add_argument("--rebrand-apply", action="store_true", help="Apply rebrand plan instead of dry run")
    parser.add_argument("--rebrand-list", action="store_true", help="List plan contents and exit")

    # Master switches
    parser.add_argument("--skip-release", action="store_true")
    parser.add_argument("--skip-rebrand", action="store_true")
    parser.add_argument("--skip-goals", action="store_true")
    parser.add_argument("--skip-change-record", action="store_true")
    parser.add_argument("--skip-checkpoint", action="store_true")
    parser.add_argument("--skip-integrity-status", action="store_true")
    parser.add_argument("--checkpoint-tag", default="workflow-harness", help="Tag label when creating an integrity checkpoint")
    parser.add_argument("--checkpoint-reason", help="Custom reason for checkpoint")
    parser.add_argument("--timeline-json", help="Path to write the run timeline as formatted JSON (overwrites)")
    parser.add_argument("--timeline-jsonl", help="Append the run summary as a JSON line to this path")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission for this harness run")
    parser.add_argument("--tail-log-source", default="workflow-harness", help="Source label used when writing tail log entries")
    parser.add_argument("--tail-log-message", help="Override the auto-generated tail log message")
    parser.add_argument("--skip-release-log", action="store_true", help="Skip appending an entry to data/logs/release.log")

    return parser


def run(args: argparse.Namespace, recorder: TelemetryRecorder | None = None) -> list[dict[str, Any]]:
    if not args.goal_date:
        args.goal_date = _utc_now().strftime("%Y-%m-%d")
    if not args.change_started:
        args.change_started = _iso_now()
    if args.change_completed is None:
        args.change_completed = ""

    timeline: list[dict[str, Any]] = []

    def _telemetry_append(entry: dict[str, Any]) -> None:
        timeline.append(entry)
        if recorder:
            recorder.record_step(
                entry["name"],
                status=entry.get("status", "unknown"),
                details=entry.get("details"),
                duration_seconds=entry.get("duration_seconds"),
            )

    def record(name: str, enabled: bool, func) -> None:
        if not enabled:
            stamp = _utc_now()
            _telemetry_append(
                {
                    "name": name,
                    "status": "skipped",
                    "details": "disabled via CLI",
                    "started_at": stamp.isoformat(),
                    "ended_at": stamp.isoformat(),
                    "duration_seconds": 0.0,
                }
            )
            return
        started = _utc_now()
        try:
            detail = func()
            status = "ok"
        except Exception as exc:  # pragma: no cover - top-level guard
            ended = _utc_now()
            _telemetry_append(
                {
                    "name": name,
                    "status": "failed",
                    "details": str(exc),
                    "started_at": started.isoformat(),
                    "ended_at": ended.isoformat(),
                    "duration_seconds": round((ended - started).total_seconds(), 3),
                }
            )
            raise
        ended = _utc_now()
        _telemetry_append(
            {
                "name": name,
                "status": status,
                "details": detail,
                "started_at": started.isoformat(),
                "ended_at": ended.isoformat(),
                "duration_seconds": round((ended - started).total_seconds(), 3),
            }
        )

    record("release pipeline", not args.skip_release, lambda: _run_release_pipeline(args))
    record("rebrand", not args.skip_rebrand, lambda: _run_rebrand(args))
    record(
        "goals log",
        not args.skip_goals,
        lambda: _update_goals_file(
            milestone=args.goal_milestone,
            summary=args.goal_summary,
            artifacts=args.goal_artifacts,
            date_str=args.goal_date,
            milestone_label=args.goal_current_label,
        ),
    )
    record(
        "change record",
        not args.skip_change_record,
        lambda: _create_change_record(
            title=args.change_title,
            tags=[t.strip() for t in args.change_tags.split(",") if t.strip()],
            owner=args.change_owner,
            status=args.change_status,
            version=args.change_version,
            started=args.change_started,
            completed=args.change_completed,
            runs=[r.strip() for r in args.change_runs.split(",") if r.strip()],
            related=args.change_related,
            intent=args.change_intent,
            fit=args.change_fit,
            validation=args.change_validation,
            risks=args.change_risks,
            master_id=args.change_master_id,
        ),
    )
    record(
        "integrity checkpoint",
        not args.skip_checkpoint,
        lambda: _checkpoint_integrity(args.checkpoint_tag, args.checkpoint_reason),
    )
    record("integrity status", not args.skip_integrity_status, _run_integrity_status)
    return timeline


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    release_entry = _initial_release_entry(args)
    summary_holder: dict[str, Any] | None = None

    def _tail_message() -> str:
        if args.tail_log_message:
            return args.tail_log_message
        if summary_holder:
            return _default_tail_log_message(summary_holder, args)
        return f"workflow harness pending · release_mode={args.release_mode}"

    release_details = {
        "release_mode": args.release_mode,
        "skip_release": args.skip_release,
        "skip_rebrand": args.skip_rebrand,
        "skip_goals": args.skip_goals,
        "skip_change_record": args.skip_change_record,
        "skip_checkpoint": args.skip_checkpoint,
        "skip_integrity_status": args.skip_integrity_status,
        "timeline_json": args.timeline_json,
        "timeline_jsonl": args.timeline_jsonl,
    }

    try:
        with telemetry_span(
            "workflow-harness",
            component="workflow_harness",
            tail_source=args.tail_log_source,
            tail_message=_tail_message,
            release_kind="workflow_harness",
            release_summary=f"workflow harness ({args.release_mode})",
            release_details=release_details,
            release_entry=release_entry,
            skip_tail_log=args.skip_tail_log,
            skip_release_log=args.skip_release_log,
        ) as recorder:
            timeline = run(args, recorder)
            summary = _build_timeline_summary(args, timeline)
            summary_holder = summary

            summary_snapshot = dict(summary)
            summary_snapshot.pop("timeline", None)
            release_entry.update(
                {
                    "timestamp": summary.get("generated_at"),
                    "timeline": timeline,
                    "summary": summary_snapshot,
                }
            )
            if recorder:
                recorder.set_metadata(
                    release_mode=args.release_mode,
                    goal=args.goal_milestone,
                    change_master=args.change_master_id,
                    timeline_entries=len(timeline),
                )

            if args.timeline_json:
                _write_json(Path(args.timeline_json), summary)
                print(f"📝 Timeline JSON written to {args.timeline_json}")
            if args.timeline_jsonl:
                _append_jsonl(Path(args.timeline_jsonl), summary)
                print(f"📝 Timeline JSONL appended to {args.timeline_jsonl}")
            if not args.skip_tail_log:
                print("🪵 Tail log entry recorded via telemetry span")
            if not args.skip_release_log:
                print("🗒️ Release log entry recorded via telemetry span")
            for entry in timeline:
                detail = entry.get("details", "") or ""
                print(f"[{entry['status']:<8}] {entry['name']}: {detail}")
            print("✅ Workflow harness completed")
            return 0
    except HarnessError as exc:
        print(f"❌ Workflow harness failed: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - final catch-all
        print(f"❌ Workflow harness failed unexpectedly: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
