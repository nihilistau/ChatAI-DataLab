#!/usr/bin/env python
"""Repo-wide lint to guard against SQLite-only instructions in docs/code."""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path
from typing import Iterable

TARGET = "interactions.db"
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops_telemetry import telemetry_span

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".project_integrity", "logs", ".venv"}
SKIP_SUBPATHS = {
    "relay/frontend/dist",
    "relay/frontend/storybook-static",
    "relay/frontend/storybook-static-relay",
    "legacy/archives/_papermill",
    "legacy/archives/notebooks/_papermill",
    "legacy/archives/notebooks/.ipynb_checkpoints",
    "workshop/notebooks/_papermill",
    "workshop/notebooks/.ipynb_checkpoints",
}
SKIP_SUFFIXES = {
    ".db",
    ".sqlite",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".gz",
    ".zip",
}
ALLOWED_GLOBS = {
    "PROJECT_OVERVIEW.md",
    "configs/lab_environment_config.md",
    "tests/test_notebooks.py",
    "tests/test_datastore_lint.py",
    "workshop/tests/test_lab_paths.py",
    "workshop/tests/test_metrics.py",
    "scripts/control_health.py",
    "scripts/datastore_lint.py",
    "relay/frontend/src/control-center/components/NotebookMonitor.tsx",
    "relay/frontend/src/control-center/components/NotebookMonitor.js",
    "relay/backend/tests/conftest.py",
    "relay/backend/app/config.py",
    "workshop/notebooks/welcome_cookbook.ipynb",
    "legacy/archives/notebooks/*.ipynb",
    "workshop/notebooks/*.ipynb",
}


class DatastoreLintError(RuntimeError):
    """Raised when forbidden references are detected."""


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in SKIP_SUBPATHS):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def _is_allowed(relative_path: str) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in ALLOWED_GLOBS)


def find_disallowed_references(root: Path | None = None) -> list[str]:
    root = root or REPO_ROOT
    violations: list[str] = []
    for path in _iter_text_files(root):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if TARGET not in content:
            continue
        rel = path.relative_to(root).as_posix()
        if _is_allowed(rel):
            continue
        for idx, line in enumerate(content.splitlines(), start=1):
            if TARGET in line:
                snippet = line.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "..."
                violations.append(f"{rel}:{idx}:{snippet}")
    return violations


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Verify datastore references stay provider-agnostic")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repo root to scan")
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="datastore-lint", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="datastore_lint", help="Release log kind label")
    parser.add_argument("--release-log-path", default=None, help="Optional release log override path")
    args = parser.parse_args(argv)

    scan_root = args.root.expanduser().resolve()
    result_holder: dict[str, int | None] = {"count": None}

    def _tail_message() -> str:
        count = result_holder["count"]
        if count is None:
            return f"datastore lint pending · root={scan_root}"
        status = "clean" if count == 0 else "violations"
        return f"datastore lint {status} · count={count}"

    release_entry = {
        "kind": "datastore_lint",
        "action": "datastore_lint",
        "root": _relativize(scan_root),
    }
    release_details = {
        "root": release_entry["root"],
    }

    try:
        with telemetry_span(
            "datastore-lint",
            component="datastore_lint",
            tail_source=args.tail_log_source,
            tail_message=_tail_message,
            release_kind=args.release_log_kind,
            release_log_path=args.release_log_path,
            release_summary="Datastore lint scan",
            release_details=release_details,
            release_entry=release_entry,
            skip_tail_log=args.skip_tail_log,
            skip_release_log=args.skip_release_log,
        ) as recorder:
            violations = find_disallowed_references(scan_root)
            result_holder["count"] = len(violations)
            status = "ok" if not violations else "failed"
            recorder.record_step(
                "scan",
                status=status,
                details={"violations": len(violations)},
            )
            release_entry["violation_count"] = len(violations)
            recorder.set_metadata(root=release_entry["root"], violations=len(violations))

            if violations:
                print("Found disallowed interactions.db references:")
                for violation in violations:
                    print(f" - {violation}")
                raise DatastoreLintError("datastore lint violations")
            print("No disallowed interactions.db references found.")
    except DatastoreLintError as exc:
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
