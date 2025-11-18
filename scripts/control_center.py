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
FRONTEND_DIR = REPO_ROOT / "chatai" / "frontend"
NOTEBOOK_PATH = REPO_ROOT / "kitchen" / "notebooks" / "control_center_playground.ipynb"
OUTPUT_DIR = NOTEBOOK_PATH.parent / "_papermill"


def run_command(command: Sequence[str], cwd: Path | None = None) -> int:
    """Run a subprocess and stream its output to the console."""

    process = subprocess.run(command, cwd=cwd or REPO_ROOT)
    return process.returncode


def cmd_start(_: argparse.Namespace) -> None:
    orchestrator = get_default_orchestrator()
    result = orchestrator.dispatch(action="start", target="all")
    print(result["output"])


def cmd_stop(_: argparse.Namespace) -> None:
    orchestrator = get_default_orchestrator()
    result = orchestrator.dispatch(action="stop", target="all")
    print(result["output"])


def cmd_status(_: argparse.Namespace) -> None:
    orchestrator = get_default_orchestrator()
    snapshot = orchestrator.snapshot(include_logs=True)
    state_dir = REPO_ROOT / ".labctl" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "aggregate.json"
    state_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps(snapshot, indent=2))


def cmd_playground(_: argparse.Namespace) -> None:
    code = run_command(["npm", "run", "playground:dev"], cwd=FRONTEND_DIR)
    if code != 0:
        sys.exit(code)


def cmd_storybook(_: argparse.Namespace) -> None:
    code = run_command(["npm", "run", "storybook"], cwd=FRONTEND_DIR)
    if code != 0:
        sys.exit(code)


def cmd_notebook(args: argparse.Namespace) -> None:
    import papermill as pm

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = OUTPUT_DIR / f"control_center_playground-cli-{timestamp}.ipynb"
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
    pm.execute_notebook(
        str(NOTEBOOK_PATH),
        str(output_path),
        parameters=parameters,
        cwd=str(NOTEBOOK_PATH.parent),
        progress_bar=False,
    )
    print(f"Notebook completed: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChatAI Control Center helper")
    subparsers = parser.add_subparsers(dest="command")

    start_cmd = subparsers.add_parser("start", help="Start backend + frontends via Lab Orchestrator")
    start_cmd.set_defaults(func=cmd_start)

    stop_cmd = subparsers.add_parser("stop", help="Stop all services via Lab Orchestrator")
    stop_cmd.set_defaults(func=cmd_stop)

    status_cmd = subparsers.add_parser("status", help="Emit orchestrator snapshot and save under .labctl/state")
    status_cmd.set_defaults(func=cmd_status)

    playground_cmd = subparsers.add_parser("playground", help="Launch the Control Center Vite dev server")
    playground_cmd.set_defaults(func=cmd_playground)

    storybook_cmd = subparsers.add_parser("storybook", help="Launch Storybook for widget development")
    storybook_cmd.set_defaults(func=cmd_storybook)

    notebook_cmd = subparsers.add_parser("notebook", help="Execute control_center_playground.ipynb via Papermill")
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
