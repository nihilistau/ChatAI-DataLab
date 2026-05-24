#!/usr/bin/env python3
"""End-to-end release automation for ChatAI · DataLab.

The pipeline intentionally mirrors the manual checklist described in
README.md, docs/RELEASE_CHECKLIST.md, and the integrity tooling guardrails.
Running this script with no arguments will:

1. Verify you are on the expected branch (defaults to `main`) and the
   working tree is clean (unless `--allow-dirty` is supplied).
2. Fetch the latest upstream refs.
3. Run `npm run check` (auto-retrying with `eslint --fix` when lint errors
   are encountered).
4. Run the Python test suite (`python -m pytest`).
5. Validate manifests, confirm integrity status is clean, and create a
   new checkpoint/tag freeze.
6. Generate release artifacts (summary markdown + tagging steps + JSON
   metadata) under `release_artifacts/<tag>/`.
7. Create and push a git tag plus the `main` branch, and append a
   structured audit record to `data/logs/release.log`.

The script is intentionally verbose so Ops can trace each guardrail. Use
`--dry-run` while developing or testing to skip the mutating actions.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
FRONTEND_DIR = ROOT / "relay" / "frontend"
MANIFESTS_DIR = ROOT / "manifests"
RELEASE_ARTIFACTS_DIR = ROOT / "release_artifacts"
RELEASE_LOG_PATH = ROOT / "data" / "logs" / "release.log"
PYTHON = sys.executable
NPM = shutil.which("npm") or shutil.which("npm.cmd") or shutil.which("npm.exe") or "npm"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_telemetry import TelemetryRecorder, telemetry_span


class ReleaseError(RuntimeError):
    """Custom exception that carries pipeline-friendly context."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().isoformat()


def _default_tag() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"v{timestamp}-control-relays"


class ReleasePipeline:
    def __init__(
        self,
        args: argparse.Namespace,
        *,
        recorder: TelemetryRecorder | None = None,
        release_entry: dict[str, Any] | None = None,
    ) -> None:
        self.args = args
        self.notes = args.notes
        self.timeline: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {
            "tag": args.tag,
            "started_at": _iso_now(),
            "branch": None,
            "commit": None,
            "checkpoint_id": None,
            "release_artifacts": None,
            "notes": args.notes,
        }
        self.release_dir = RELEASE_ARTIFACTS_DIR / args.tag
        self.release_actions_performed = False
        self.release_log_recorded = False
        self.recorder = recorder
        self.release_entry = release_entry if release_entry is not None else {}
        self.release_entry.setdefault("tag", args.tag)
        self.release_entry.setdefault("release_tag", args.tag)
        self.release_entry.setdefault("release_mode", "dry-run" if self.args.dry_run else "full")
        self.skip_release_log_effective = (
            self.args.skip_release_log or self.args.dry_run or self.args.skip_integrity
        )
        self.telemetry_release_enabled = False
        self.telemetry_tail_enabled = False
        self._sync_telemetry_flags()

    def _sync_telemetry_flags(self) -> None:
        recorder_present = self.recorder is not None
        self.telemetry_release_enabled = recorder_present and not self.skip_release_log_effective
        self.telemetry_tail_enabled = recorder_present and not self.args.skip_tail_log

    def attach_recorder(self, recorder: TelemetryRecorder | None) -> None:
        self.recorder = recorder
        self._sync_telemetry_flags()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> None:
        branch = self._current_branch()
        self.summary["branch"] = branch
        if self.args.branch and branch != self.args.branch:
            raise ReleaseError(
                f"Expected branch '{self.args.branch}' but found '{branch}'. "
                "Use --branch to override if this is intentional."
            )
        self.summary["commit"] = self._current_commit()

        if self.args.allow_dirty:
            self._append_timeline_entry(
                "worktree check",
                "skipped",
                "Skipped clean check via --allow-dirty (not recommended for real releases)",
            )
        else:
            self._record_step("worktree clean", self._assert_clean_worktree)

        self._record_step("fetch origin", self._git_fetch)

        if self.args.skip_tests:
            self._append_timeline_entry(
                "tests",
                "skipped",
                "User supplied --skip-tests; guardrails only",
            )
        else:
            self._record_step("npm run check", self._run_frontend_checks_with_autofix)
            self._record_step("pytest", self._run_pytests)

        self._record_step("manifest validation", self._validate_manifests)
        if self.args.skip_integrity:
            self._append_timeline_entry(
                "integrity status",
                "skipped",
                "--skip-integrity supplied; manifest hash diff not enforced",
            )
        else:
            self._record_step("integrity status", self._assert_integrity_clean)

        if self.args.dry_run or self.args.skip_integrity:
            self._append_timeline_entry(
                "checkpoint",
                "skipped",
                "Dry-run mode or --skip-integrity leaves checkpoints/tags untouched",
            )
            self._append_timeline_entry(
                "release log",
                "skipped",
                "Dry-run mode or --skip-integrity leaves release log untouched",
            )
        else:
            self.release_actions_performed = True
            checkpoint_id = self._record_step("checkpoint", self._create_checkpoint)
            self.summary["checkpoint_id"] = checkpoint_id
            artifacts = self._record_step("release artifacts", self._write_release_artifacts)
            self.summary["release_artifacts"] = artifacts
            self._record_step("git tag", self._create_tag)
            if self.args.push:
                self._record_step("git push", self._push_refs)
            else:
                self._append_timeline_entry(
                    "git push",
                    "skipped",
                    "--no-push was supplied; remember to push refs manually",
                )
            if self.args.skip_release_log:
                self._append_timeline_entry(
                    "release log",
                    "skipped",
                    "--skip-release-log supplied",
                )
            elif self.telemetry_release_enabled:
                self.release_log_recorded = True
                self._append_timeline_entry(
                    "release log",
                    "ok",
                    "Telemetry span configured to append release log entry",
                )
            else:
                self._record_step("release log", self._append_release_log)
                self.release_log_recorded = True

        if self.args.skip_tail_log:
            self._append_timeline_entry("tail log", "skipped", "--skip-tail-log supplied")
        elif self.telemetry_tail_enabled:
            self._append_timeline_entry(
                "tail log",
                "ok",
                "Telemetry span emitted tail log entry",
            )
        else:
            self._record_step("tail log", self._emit_tail_log_entry)

        self.summary["finished_at"] = _iso_now()

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------
    def _record_step(self, name: str, func: Callable[[], Any]) -> Any:
        started = _now()
        entry: dict[str, Any] = {
            "name": name,
            "started_at": started.isoformat(),
            "status": "running",
        }
        try:
            result = func()
        except Exception as exc:  # pragma: no cover - defensive logging
            ended = _now()
            entry["status"] = "failed"
            entry["ended_at"] = ended.isoformat()
            entry["duration_seconds"] = round((ended - started).total_seconds(), 3)
            entry["error"] = str(exc)
            self.timeline.append(entry)
            self._record_telemetry_step(
                name,
                status="failed",
                details=str(exc),
                duration=entry.get("duration_seconds"),
            )
            raise
        ended = _now()
        entry["status"] = "ok"
        entry["ended_at"] = ended.isoformat()
        entry["duration_seconds"] = round((ended - started).total_seconds(), 3)
        if result is not None:
            entry["details"] = result
        self.timeline.append(entry)
        self._record_telemetry_step(
            name,
            status="ok",
            details=result,
            duration=entry.get("duration_seconds"),
        )
        return result

    def _append_timeline_entry(self, name: str, status: str, details: str) -> None:
        stamp = _now()
        self.timeline.append(
            {
                "name": name,
                "status": status,
                "started_at": stamp.isoformat(),
                "ended_at": stamp.isoformat(),
                "duration_seconds": 0.0,
                "details": details,
            }
        )
        self._record_telemetry_step(name, status=status, details=details, duration=0.0)

    def _record_telemetry_step(
        self,
        name: str,
        *,
        status: str,
        details: Any | None,
        duration: float | None,
    ) -> None:
        if not self.recorder:
            return
        self.recorder.record_step(
            name,
            status=status,
            details=details,
            duration_seconds=duration,
        )

    def _build_release_entry(self) -> dict[str, Any]:
        finished_at = self.summary.get("finished_at") or _iso_now()
        payload: dict[str, Any] = {
            "timestamp": finished_at,
            "kind": "release_pipeline",
            "action": "release_pipeline",
            "tag": self.args.tag,
            "release_tag": self.args.tag,
            "branch": self.summary.get("branch"),
            "commit": self.summary.get("commit"),
            "checkpoint_id": self.summary.get("checkpoint_id"),
            "release_artifacts": self.summary.get("release_artifacts"),
            "release_dir": str(self.release_dir.relative_to(ROOT)) if self.release_dir.exists() else None,
            "timeline": self.timeline,
            "notes": self.summary.get("notes"),
            "release_mode": "dry-run" if self.args.dry_run else "full",
        }
        if not self.summary.get("release_artifacts"):
            payload.pop("release_dir", None)
        self.release_entry.update({k: v for k, v in payload.items() if v is not None})
        return dict(self.release_entry)

    # ------------------------------------------------------------------
    # Individual steps
    # ------------------------------------------------------------------
    def _run_command(self, command: Sequence[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess:
        readable = " ".join(command)
        print(f"→ {readable}")
        result = subprocess.run(
            command,
            cwd=cwd or ROOT,
            text=True,
            capture_output=capture,
            check=False,
        )
        if result.returncode != 0:
            raise ReleaseError(
                textwrap.dedent(
                    f"""
                    Command `{readable}` failed with exit code {result.returncode}
                    STDOUT:\n{result.stdout.strip()}\n
                    STDERR:\n{result.stderr.strip()}
                    """
                ).strip()
            )
        if capture:
            return result
        return result

    def _current_branch(self) -> str:
        result = self._run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        return result.stdout.strip()

    def _current_commit(self) -> str:
        result = self._run_command(["git", "rev-parse", "HEAD"], capture=True)
        return result.stdout.strip()

    def _assert_clean_worktree(self) -> str:
        result = self._run_command(["git", "status", "--porcelain"], capture=True)
        dirty = result.stdout.strip()
        if dirty:
            raise ReleaseError(
                "Working tree has local modifications. Commit, stash, or clean before running the release pipeline."
            )
        return "worktree clean"

    def _git_fetch(self) -> str:
        self._run_command(["git", "fetch", "--prune", "origin"])
        return "origin fetched"

    def _run_frontend_checks_with_autofix(self) -> str:
        try:
            self._run_command([NPM, "run", "check"], cwd=FRONTEND_DIR)
            return "npm run check passed"
        except ReleaseError as err:
            if not self.args.auto_fix:
                raise
            print("npm run check failed; attempting eslint --fix before retrying")
            self._run_command([NPM, "run", "lint", "--", "--fix"], cwd=FRONTEND_DIR)
            self._run_command([NPM, "run", "check"], cwd=FRONTEND_DIR)
            return f"npm run check passed after --fix ({err})"

    def _run_pytests(self) -> str:
        self._run_command([PYTHON, "-m", "pytest"])
        return "pytest suite passed"

    def _validate_manifests(self) -> str:
        if not MANIFESTS_DIR.exists():
            return "manifests directory missing; skipped"
        cmd = [
            PYTHON,
            str(SCRIPTS_DIR / "manifest_validator.py"),
            str(MANIFESTS_DIR),
            "--pattern",
            "*.json",
            "--json",
        ]
        result = self._run_command(cmd, capture=True)
        payload = result.stdout.strip()
        if payload:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ReleaseError(f"Unable to parse manifest validator output: {exc}\n{payload}") from exc
            print(payload)
            return f"Validated {len(data)} manifest payload(s)"
        return "No manifest payloads detected"

    def _assert_integrity_clean(self) -> dict[str, int]:
        result = self._run_command(
            [PYTHON, str(SCRIPTS_DIR / "project_integrity.py"), "status"],
            capture=True,
        )
        output = result.stdout.strip()
        print(output)
        first_json_line = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                first_json_line = line
                break
        if not first_json_line:
            raise ReleaseError("Integrity status did not emit a JSON summary")
        summary = json.loads(first_json_line)
        if any(summary.values()):
            raise ReleaseError(
                f"Integrity manifest drift detected: {summary}. Run the fixer commands before retrying the release pipeline."
            )
        return summary

    def _create_checkpoint(self) -> str:
        reason = f"release freeze {self.args.tag}"
        result = self._run_command(
            [
                PYTHON,
                str(SCRIPTS_DIR / "project_integrity.py"),
                "checkpoint",
                "--tag",
                self.args.tag,
                "--reason",
                reason,
            ],
            capture=True,
        )
        print(result.stdout.strip())
        match = re.search(r"Checkpoint\s+(\d+)\s+created", result.stdout)
        return match.group(1) if match else "unknown"

    def _write_release_artifacts(self) -> dict[str, Any]:
        if self.release_dir.exists():
            if not self.args.force_release_dir:
                raise ReleaseError(
                    f"Release artifact directory {self.release_dir} already exists. Pass --force-release-dir to overwrite."
                )
            shutil.rmtree(self.release_dir)
        self.release_dir.mkdir(parents=True, exist_ok=True)

        steps_table = "| Step | Status | Duration (s) | Details |\n| --- | --- | --- | --- |\n"
        for entry in self.timeline:
            details = entry.get("details", "")
            if isinstance(details, str):
                safe_details = details.replace("\n", " ")
            elif details is None:
                safe_details = ""
            else:
                safe_details = json.dumps(details, ensure_ascii=False)
            steps_table += f"| {entry['name']} | {entry['status']} | {entry.get('duration_seconds', 0)} | {safe_details} |\n"

        finished_at = self.summary.get("finished_at") or _iso_now()
        notes_line = f"\n- Notes: {self.summary['notes']}" if self.summary.get("notes") else ""
        summary_md = textwrap.dedent(
            f"""
            # Release summary — {self.args.tag}

            - Timestamp: {finished_at}
            - Branch: {self.summary['branch']}
            - Commit: {self.summary['commit']}
            - Checkpoint: {self.summary.get('checkpoint_id', 'n/a')}{notes_line}

            ## Steps
            {steps_table}
            """
        ).strip()
        (self.release_dir / "RELEASE_SUMMARY.md").write_text(summary_md + "\n", encoding="utf-8")

        tag_message = self.args.tag_message or f"Release {self.args.tag}"
        tagging_md = textwrap.dedent(
            f"""
            # Tagging and push steps

            ```powershell
            cd "{ROOT}"
            git status
            git tag -a {self.args.tag} -m "{tag_message}"
            git push origin {self.summary['branch']}
            git push origin {self.args.tag}
            ```
            """
        ).strip()
        (self.release_dir / "TAGGING_STEPS.md").write_text(tagging_md + "\n", encoding="utf-8")

        meta_payload = {
            "summary": self.summary,
            "timeline": self.timeline,
        }
        (self.release_dir / "release_meta.json").write_text(json.dumps(meta_payload, indent=2) + "\n", encoding="utf-8")
        return {
            "path": str(self.release_dir.relative_to(ROOT)),
            "summary_file": str((self.release_dir / "RELEASE_SUMMARY.md").relative_to(ROOT)),
        }

    def _create_tag(self) -> str:
        if self.args.dry_run:
            return "skipped"
        existing = self._run_command(["git", "tag", "-l", self.args.tag], capture=True).stdout.strip()
        if existing:
            raise ReleaseError(f"Git tag {self.args.tag} already exists")
        tag_message = self.args.tag_message or f"Release {self.args.tag}"
        self._run_command(["git", "tag", "-a", self.args.tag, "-m", tag_message])
        return self.args.tag

    def _push_refs(self) -> str:
        if self.args.dry_run:
            return "skipped"
        self._run_command(["git", "push", "origin", self.summary["branch"]])
        self._run_command(["git", "push", "origin", self.args.tag])
        return "pushed"

    def _append_release_log(self) -> str:
        RELEASE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = self._build_release_entry()
        with RELEASE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        return str(RELEASE_LOG_PATH.relative_to(ROOT))

    def _default_tail_log_message(self) -> str:
        branch = self.summary.get("branch") or "unknown"
        mode = "dry-run" if self.args.dry_run else "full"
        release_state = "completed" if self.release_actions_performed else "skipped"
        log_state = "written" if self.release_log_recorded else "skipped"
        return (
            f"release pipeline {mode} · tag={self.args.tag} · branch={branch} "
            f"· release_step={release_state} · release_log={log_state}"
        )

    def _emit_tail_log_entry(self) -> str:
        message = self.args.tail_log_message or self._default_tail_log_message()
        cmd = [
            PYTHON,
            str(SCRIPTS_DIR / "relay_store.py"),
            "tail-log-add",
            message,
            "--source",
            self.args.tail_log_source,
        ]
        try:
            self._run_command(cmd)
            return f"Tail log entry recorded · {self.args.tail_log_source}"
        except ReleaseError as exc:
            return f"Tail log entry skipped: {exc}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze + release automation for ChatAI · DataLab")
    parser.add_argument("--tag", help="Release tag to create (defaults to vYYYYMMDD-HHMMSS-control-relays)")
    parser.add_argument("--tag-message", dest="tag_message", help="Custom git tag message")
    parser.add_argument("--branch", default="main", help="Expected branch name")
    parser.add_argument("--dry-run", action="store_true", help="Run validations only; skip checkpoint/tag/push")
    parser.add_argument("--skip-tests", action="store_true", help="Skip npm/pytest (not recommended)")
    parser.add_argument("--skip-integrity", action="store_true", help="Skip integrity status + checkpoint (dev use only)")
    parser.add_argument("--auto-fix", dest="auto_fix", action="store_true", help="Allow eslint --fix retries (default)")
    parser.add_argument("--no-auto-fix", dest="auto_fix", action="store_false", help="Disable eslint autofix retries")
    parser.add_argument("--push", dest="push", action="store_true", help="Push branch + tag (default)")
    parser.add_argument("--no-push", dest="push", action="store_false", help="Skip pushing refs")
    parser.add_argument("--allow-dirty", action="store_true", help="Bypass clean worktree check (dev testing only)")
    parser.add_argument("--force-release-dir", action="store_true", help="Overwrite existing release artifact directory")
    parser.add_argument("--notes", help="Optional note to embed in release artifacts and logs")
    parser.add_argument("--skip-release-log", action="store_true", help="Skip writing to data/logs/release.log")
    parser.add_argument("--skip-tail-log", action="store_true", help="Skip emitting a tail log entry when the pipeline completes")
    parser.add_argument("--tail-log-source", default="release-pipeline", help="Source label for the tail log entry")
    parser.add_argument("--tail-log-message", help="Override the auto-generated tail log message")
    parser.set_defaults(auto_fix=True, push=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.tag:
        args.tag = _default_tag()
    pipeline = ReleasePipeline(args)

    def _tail_message() -> str:
        return pipeline._default_tail_log_message()

    release_details = {
        "tag": args.tag,
        "notes": args.notes,
        "push": args.push,
        "branch": args.branch,
        "dry_run": args.dry_run,
    }

    try:
        with telemetry_span(
            "release_pipeline",
            component="release_pipeline",
            tail_source=args.tail_log_source,
            tail_message=_tail_message,
            release_kind="release_pipeline",
            release_log_path=RELEASE_LOG_PATH,
            release_summary=f"release pipeline · {args.tag}",
            release_details={k: v for k, v in release_details.items() if v is not None},
            release_entry=pipeline.release_entry,
            skip_tail_log=args.skip_tail_log,
            skip_release_log=pipeline.skip_release_log_effective,
        ) as recorder:
            pipeline.attach_recorder(recorder)
            try:
                pipeline.run()
            finally:
                payload = pipeline._build_release_entry()
                if recorder:
                    recorder.set_metadata(
                        tag=args.tag,
                        branch=pipeline.summary.get("branch"),
                        commit=pipeline.summary.get("commit"),
                        checkpoint=pipeline.summary.get("checkpoint_id"),
                        release_artifacts=pipeline.summary.get("release_artifacts"),
                        release_entry_path=payload.get("release_dir"),
                    )
    except ReleaseError as exc:
        print(f"❌ Release automation failed: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - final catch-all
        print(f"❌ Unexpected failure: {exc}")
        return 1
    print("✅ Release automation completed successfully")
    print(f"Tag: {args.tag}")
    if pipeline.summary.get("checkpoint_id"):
        print(f"Checkpoint: {pipeline.summary['checkpoint_id']}")
    if pipeline.summary.get("release_artifacts"):
        print(f"Release artifacts: {pipeline.summary['release_artifacts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
