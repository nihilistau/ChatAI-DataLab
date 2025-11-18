#!/usr/bin/env python
"""Repo-wide lint to guard against SQLite-only instructions in docs/code."""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
from typing import Iterable

TARGET = "interactions.db"
REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".project_integrity", "logs", ".venv"}
SKIP_SUBPATHS = {
    "playground/frontend/dist",
    "playground/frontend/storybook-static",
    "playground/frontend/storybook-static-playground",
    "legacy/datalab/_papermill",
    "legacy/datalab/notebooks/_papermill",
    "legacy/datalab/notebooks/.ipynb_checkpoints",
    "kitchen/notebooks/_papermill",
    "kitchen/notebooks/.ipynb_checkpoints",
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
    "kitchen/tests/test_lab_paths.py",
    "kitchen/tests/test_metrics.py",
    "scripts/control_health.py",
    "scripts/datastore_lint.py",
    "playground/frontend/src/control-center/components/NotebookMonitor.tsx",
    "playground/frontend/src/control-center/components/NotebookMonitor.js",
    "playground/backend/tests/conftest.py",
    "playground/backend/app/config.py",
    "kitchen/notebooks/welcome_cookbook.ipynb",
    "legacy/datalab/notebooks/*.ipynb",
    "kitchen/notebooks/*.ipynb",
}


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify datastore references stay provider-agnostic")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repo root to scan")
    args = parser.parse_args()
    violations = find_disallowed_references(args.root)
    if violations:
        print("Found disallowed interactions.db references:")
        for violation in violations:
            print(f" - {violation}")
        raise SystemExit(1)
    print("No disallowed interactions.db references found.")


if __name__ == "__main__":
    main()
