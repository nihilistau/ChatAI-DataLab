"""Shared helpers for resolving repository-relative paths in notebooks and scripts."""
# @tag: datalab,paths

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Union

Pathish = Union[str, os.PathLike[str]]


@lru_cache(maxsize=1)
def get_lab_root() -> Path:
    """Return the canonical repository root, honoring LAB_ROOT when provided."""

    env_override = os.environ.get("LAB_ROOT")
    if env_override:
        return Path(env_override).expanduser().resolve()

    # Module lives under <repo>/datalab, so ascend one level by default.
    return Path(__file__).resolve().parents[1]


def lab_path(*segments: Pathish) -> Path:
    """Join segments onto the repository root."""

    root = get_lab_root()
    return root.joinpath(*segments)


def data_path(*segments: Pathish) -> Path:
    """Convenience helper to join under the shared data directory."""

    return lab_path("data", *segments)


def logs_path(*segments: Pathish) -> Path:
    """Convenience helper to join under the structured logs directory."""

    return data_path("logs", *segments)


def ensure_directory(path: Path) -> Path:
    """Create parent directories for the provided path and return the resolved Path."""

    resolved = Path(path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def describe_environment(extras: dict | None = None) -> dict:
    """Return a structured snapshot of the runtime environment for diagnostics."""

    snapshot: dict[str, object] = {
        "lab_root": str(get_lab_root()),
        "lab_root_env": os.environ.get("LAB_ROOT"),
        "cwd": str(Path.cwd()),
        "python_executable": os.environ.get("PYTHONEXECUTABLE") or Path(sys.executable).as_posix(),
    }
    if extras:
        snapshot.update(extras)
    return snapshot


def iter_search_paths(base: Path | None = None) -> Iterable[Path]:
    """Yield interesting search paths for troubleshooting."""

    root = base or get_lab_root()
    yield root
    yield root / "data"
    yield root / "datalab"
    yield root / "chatai" / "backend"
    yield root / "configs"
