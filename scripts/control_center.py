#!/usr/bin/env python
"""Developer-facing automation helpers for the Control Center system."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controlplane import get_default_orchestrator
from scripts import rebrand_reset
from scripts.ops_telemetry import telemetry_span

FRONTEND_DIR = REPO_ROOT / "relay" / "frontend"
NOTEBOOK_PATH = REPO_ROOT / "workshop" / "notebooks" / "control_center_relay.ipynb"
OUTPUT_DIR = NOTEBOOK_PATH.parent / "_papermill"
WORKFLOW_SCRIPT = REPO_ROOT / "scripts" / "workflow_harness.py"


def run_command(command: Sequence[str], cwd: Path | None = None) -> int:
    """Run a subprocess and stream its output to the console."""

    process = subprocess.run(command, cwd=cwd or REPO_ROOT)
    return process.returncode


def _telemetry_span(args: argparse.Namespace, action: str, **kwargs):
    return telemetry_span(
        action,
        component="control_center",
        tail_source=args.tail_log_source,
        release_kind=args.release_log_kind,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
        **kwargs,
    )


def _trim(text: str, limit: int = 400) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def cmd_start(args: argparse.Namespace) -> None:
    with _telemetry_span(args, "start", release_summary="Start orchestrator") as span:
        orchestrator = get_default_orchestrator()
        result = orchestrator.dispatch(action="start", target="all")
        span.record_step("orchestrator", details={"action": "start", "target": "all"})
        span.set_metadata(output=_trim(result["output"]))
        print(result["output"])


def cmd_stop(args: argparse.Namespace) -> None:
    with _telemetry_span(args, "stop", release_summary="Stop orchestrator") as span:
        orchestrator = get_default_orchestrator()
        result = orchestrator.dispatch(action="stop", target="all")
        span.record_step("orchestrator", details={"action": "stop", "target": "all"})
        span.set_metadata(output=_trim(result["output"]))
        print(result["output"])


def cmd_status(args: argparse.Namespace) -> None:
    with _telemetry_span(args, "status", release_summary="Snapshot orchestrator state") as span:
        orchestrator = get_default_orchestrator()
        snapshot = orchestrator.snapshot(include_logs=True)
        state_dir = REPO_ROOT / ".labctl" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / "aggregate.json"
        state_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        span.record_step("snapshot", details={"path": str(state_path)})
        print(json.dumps(snapshot, indent=2))


def cmd_relay(args: argparse.Namespace) -> None:
    with _telemetry_span(args, "relay-dev", release_summary="Launch Relay dev server") as span:
        code = run_command(["npm", "run", "relay:dev"], cwd=FRONTEND_DIR)
        status = "ok" if code == 0 else "failed"
        span.record_step("relay:dev", status=status, details={"exit_code": code})
        if code != 0:
            raise SystemExit(code)


def cmd_storybook(args: argparse.Namespace) -> None:
    with _telemetry_span(args, "storybook", release_summary="Launch Storybook") as span:
        code = run_command(["npm", "run", "storybook"], cwd=FRONTEND_DIR)
        status = "ok" if code == 0 else "failed"
        span.record_step("storybook", status=status, details={"exit_code": code})
        if code != 0:
            raise SystemExit(code)


def cmd_rebrand(args: argparse.Namespace) -> None:
    argv: list[str] = []
    if args.config:
        argv.extend(["--config", args.config])
    if args.steps:
        argv.append("--steps")
        argv.extend(args.steps)
    if args.dry_run:
        argv.append("--dry-run")
    if args.list:
        argv.append("--list")
    with _telemetry_span(args, "rebrand", release_summary="Invoke rebrand workflow") as span:
        span.set_metadata(config=args.config or "default", dry_run=args.dry_run, steps=args.steps or "all")
        rebrand_reset.main(argv)


def cmd_workflow(args: argparse.Namespace) -> None:
    command = [sys.executable, str(WORKFLOW_SCRIPT)]
    if args.forward:
        command.extend(args.forward)
    with _telemetry_span(args, "workflow", release_summary="Run workflow harness") as span:
        span.set_metadata(argv=" ".join(command[2:]) if len(command) > 2 else "")
        code = run_command(command)
        status = "ok" if code == 0 else "failed"
        span.record_step("workflow_harness", status=status, details={"exit_code": code})
        if code != 0:
            raise SystemExit(code)


def cmd_notebook(args: argparse.Namespace) -> None:
    import papermill as pm

    with _telemetry_span(args, "notebook", release_summary="Execute Control Center notebook") as span:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = OUTPUT_DIR / f"control_center_relay-cli-{timestamp}.ipynb"
        db_override: str | None = None
        if args.db_path:
            if args.db_path.lower() != "auto":
                db_path = Path(args.db_path)
                if not db_path.is_absolute():
                    db_path = (REPO_ROOT / db_path).resolve()
                db_override = str(db_path)
        parameters = {
            "DB_PATH": db_override,
            "CONTROL_STATUS_URL": args.status_url,
            "OUTPUT_DIR": str(OUTPUT_DIR),
        }
        span.set_metadata(db_override=db_override or "auto", status_url=args.status_url)
        pm.execute_notebook(
            str(NOTEBOOK_PATH),
            str(output_path),
            parameters=parameters,
            cwd=str(NOTEBOOK_PATH.parent),
            progress_bar=False,
        )
        span.record_step("papermill", details={"output": str(output_path)})
        print(f"Notebook completed: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChatAI Control Center helper")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument(
        "--tail-log-source",
        default="control-center",
        help="Source label recorded in the tail log",
    )
    parser.add_argument(
        "--release-log-kind",
        default="control_center_cli",
        help="Kind label used for release log entries",
    )
    subparsers = parser.add_subparsers(dest="command")

    start_cmd = subparsers.add_parser("start", help="Start backend + frontends via Lab Orchestrator")
    start_cmd.set_defaults(func=cmd_start)

    stop_cmd = subparsers.add_parser("stop", help="Stop all services via Lab Orchestrator")
    stop_cmd.set_defaults(func=cmd_stop)

    status_cmd = subparsers.add_parser("status", help="Emit orchestrator snapshot and save under .labctl/state")
    status_cmd.set_defaults(func=cmd_status)

    relay_cmd = subparsers.add_parser("relay", help="Launch the Control Center Vite dev server")
    relay_cmd.set_defaults(func=cmd_relay)

    storybook_cmd = subparsers.add_parser("storybook", help="Launch Storybook for widget development")
    storybook_cmd.set_defaults(func=cmd_storybook)

    notebook_cmd = subparsers.add_parser("notebook", help="Execute control_center_relay.ipynb via Papermill")
    notebook_cmd.add_argument(
        "--db-path",
        default=None,
        help="Optional SQLite path override. Omit or pass 'auto' to use the configured data store",
    )
    notebook_cmd.add_argument(
        "--status-url",
        default="http://localhost:8000/api/control/status",
        help="Control status endpoint to query",
    )
    notebook_cmd.set_defaults(func=cmd_notebook)

    rebrand_cmd = subparsers.add_parser(
        "rebrand",
        help="Run the config-driven rename/reset workflow (wrapping scripts/rebrand_reset.py)",
    )
    rebrand_cmd.add_argument(
        "--config",
        default=None,
        help="Path to the rebrand config JSON (defaults to scripts/rebrand_reset.py internal value)",
    )
    rebrand_cmd.add_argument(
        "--steps",
        choices=rebrand_reset.STEP_CHOICES,
        nargs="*",
        default=None,
        help="Optionally limit execution to certain steps",
    )
    rebrand_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the plan without modifying files",
    )
    rebrand_cmd.add_argument(
        "--list",
        action="store_true",
        help="List plan stats and exit",
    )
    rebrand_cmd.set_defaults(func=cmd_rebrand)

    workflow_cmd = subparsers.add_parser(
        "workflow",
        help="Run the composite release + docs + change logging harness (wraps scripts/workflow_harness.py)",
    )
    workflow_cmd.add_argument(
        "forward",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to workflow_harness.py (prefix with -- to separate)",
    )
    workflow_cmd.set_defaults(func=cmd_workflow)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
