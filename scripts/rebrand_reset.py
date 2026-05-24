#!/usr/bin/env python3
"""Utility to orchestrate wide renames / replacements for Control Center resets.

The workflow mirrors the recent Horizon Relay conversion:
1. Perform path-level moves / copies.
2. Apply high-volume text replacements with guardrails.
3. Trigger the standard validation commands (pytest, npm run check, etc.).

All behavior is driven by a JSON configuration file so future rebrands can
reuse the same playbook with new token pairs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops_telemetry import telemetry_span
DEFAULT_CONFIG = REPO_ROOT / "configs" / "rebrand_plan.example.json"
STEP_CHOICES = ("renames", "copies", "replacements", "commands")
DEFAULT_EXCLUDES = [
    ".git/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/__pycache__/**",
    "**/dist/**",
    "**/build/**",
    "**/storybook-static*/**",
]


@dataclass
class RenameSpec:
    source: str
    target: str

    def resolved(self) -> tuple[Path, Path]:
        return (REPO_ROOT / self.source).resolve(), (REPO_ROOT / self.target).resolve()


@dataclass
class CopySpec:
    source: str
    target: str
    overwrite: bool = True

    def resolved(self) -> tuple[Path, Path]:
        return (REPO_ROOT / self.source).resolve(), (REPO_ROOT / self.target).resolve()


@dataclass
class ReplacementSpec:
    find: str
    replace: str
    globs: Sequence[str] = field(default_factory=lambda: ("**/*",))
    excludes: Sequence[str] = field(default_factory=list)


@dataclass
class CommandSpec:
    name: str
    cmd: Sequence[str]
    cwd: str | None = None
    continue_on_error: bool = False

    def resolved_cwd(self) -> Path:
        return (REPO_ROOT / self.cwd).resolve() if self.cwd else REPO_ROOT


@dataclass
class RebrandPlan:
    renames: list[RenameSpec] = field(default_factory=list)
    copies: list[CopySpec] = field(default_factory=list)
    replacements: list[ReplacementSpec] = field(default_factory=list)
    commands: list[CommandSpec] = field(default_factory=list)

    @classmethod
    def from_json(cls, payload: dict) -> "RebrandPlan":
        return cls(
            renames=[RenameSpec(**item) for item in payload.get("renames", [])],
            copies=[CopySpec(**item) for item in payload.get("copies", [])],
            replacements=[ReplacementSpec(**item) for item in payload.get("replacements", [])],
            commands=[CommandSpec(**item) for item in payload.get("commands", [])],
        )


def _matches_pattern(rel_path: str, pattern: str) -> bool:
    from fnmatch import fnmatch

    return fnmatch(rel_path, pattern)


def _should_skip(rel_path: str, custom_excludes: Sequence[str]) -> bool:
    for pattern in (*DEFAULT_EXCLUDES, *custom_excludes):
        if _matches_pattern(rel_path, pattern):
            return True
    return False


def _iter_files(globs: Sequence[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for candidate in REPO_ROOT.glob(pattern):
            if candidate.is_file() and candidate not in seen:
                seen.add(candidate)
                yield candidate


def perform_renames(plan: RebrandPlan, *, dry_run: bool) -> int:
    executed = 0
    for spec in plan.renames:
        src, dst = spec.resolved()
        if not src.exists():
            print(f"[renames] skip {src} (missing)")
            continue
        if dry_run:
            print(f"[renames] would rename {src} -> {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"[renames] {src} -> {dst}")
        src.rename(dst)
        executed += 1
    return executed


def perform_copies(plan: RebrandPlan, *, dry_run: bool) -> int:
    executed = 0
    for spec in plan.copies:
        src, dst = spec.resolved()
        if not src.exists():
            print(f"[copies] skip {src} (missing)")
            continue
        if not spec.overwrite and dst.exists():
            print(f"[copies] skip {dst} (exists, overwrite disabled)")
            continue
        if dry_run:
            print(f"[copies] would copy {src} -> {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        dst.write_bytes(data)
        print(f"[copies] {src} -> {dst}")
        executed += 1
    return executed


def perform_replacements(plan: RebrandPlan, *, dry_run: bool) -> int:
    total_touched = 0
    for spec in plan.replacements:
        updated_files = 0
        for path in _iter_files(spec.globs):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if _should_skip(rel, spec.excludes):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if spec.find not in text:
                continue
            replaced = text.replace(spec.find, spec.replace)
            if replaced == text:
                continue
            updated_files += 1
            if dry_run:
                print(f"[replace] {rel}: would replace '{spec.find}' -> '{spec.replace}'")
            else:
                path.write_text(replaced, encoding="utf-8")
        print(f"[replace] '{spec.find}' -> '{spec.replace}' touched {updated_files} files")
        total_touched += updated_files
    return total_touched


def run_commands(plan: RebrandPlan, *, dry_run: bool) -> int:
    executed = 0
    for spec in plan.commands:
        cmd_display = " ".join(spec.cmd)
        if dry_run:
            print(f"[command] would run ({spec.name}): {cmd_display}")
            continue
        print(f"[command] running ({spec.name}): {cmd_display}")
        proc = subprocess.run(spec.cmd, cwd=spec.resolved_cwd(), check=False)
        if proc.returncode != 0:
            message = f"[command] {spec.name} failed with code {proc.returncode}"
            if spec.continue_on_error:
                print(message)
            else:
                raise SystemExit(message)
        executed += 1
    return executed


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate rename + validation workflows")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to rebrand plan JSON")
    parser.add_argument(
        "--steps",
        choices=STEP_CHOICES,
        nargs="*",
        default=list(STEP_CHOICES),
        help="Limit execution to specific steps",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying files")
    parser.add_argument("--list", action="store_true", help="Print a summary of the loaded plan and exit")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument(
        "--tail-log-source", default="rebrand", help="Source label when emitting tail log entries"
    )
    parser.add_argument(
        "--release-kind", default="rebrand_workflow", help="Kind label for release log entries"
    )
    parser.add_argument(
        "--release-log-path",
        default=None,
        help="Optional override for the release log path (defaults to settings.release_log_path)",
    )
    return parser.parse_args(argv)


def load_plan(config_path: str) -> RebrandPlan:
    path = Path(config_path).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    if not path.exists():
        raise SystemExit(f"Config file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RebrandPlan.from_json(payload)


def summarize_plan(plan: RebrandPlan) -> None:
    print("Loaded plan:")
    print(f"  renames: {len(plan.renames)}")
    print(f"  copies: {len(plan.copies)}")
    print(f"  replacements: {len(plan.replacements)}")
    print(f"  commands: {len(plan.commands)}")


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    plan = load_plan(args.config)
    summarize_plan(plan)
    if args.list:
        return

    selected = set(args.steps)
    summary = "Dry-run rebrand plan" if args.dry_run else "Apply rebrand plan"
    details = {
        "config": str(args.config),
        "steps": list(selected),
        "dry_run": args.dry_run,
    }
    with telemetry_span(
        "rebrand-reset",
        component="rebrand_reset",
        tail_source=args.tail_log_source,
        release_kind=args.release_kind,
        release_log_path=args.release_log_path,
        release_summary=summary,
        release_details=details,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as span:
        if "renames" in selected:
            touched = perform_renames(plan, dry_run=args.dry_run)
            span.record_step("renames", details={"count": touched, "dry_run": args.dry_run})
        if "copies" in selected:
            touched = perform_copies(plan, dry_run=args.dry_run)
            span.record_step("copies", details={"count": touched, "dry_run": args.dry_run})
        if "replacements" in selected:
            touched = perform_replacements(plan, dry_run=args.dry_run)
            span.record_step("replacements", details={"files": touched, "dry_run": args.dry_run})
        if "commands" in selected:
            touched = run_commands(plan, dry_run=args.dry_run)
            span.record_step("commands", details={"count": touched, "dry_run": args.dry_run})


if __name__ == "__main__":
    main()
