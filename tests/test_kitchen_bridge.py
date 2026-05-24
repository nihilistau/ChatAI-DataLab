"""Ensure the Workshop namespace stands alone while legacy notebooks stay archived."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import workshop

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ARCHIVES = REPO_ROOT / "legacy" / "archives"


def test_legacy_archives_are_read_only():
    """`legacy/archives` should exist for historical notebook reference but not import."""

    assert LEGACY_ARCHIVES.exists(), "legacy/archives should remain as read-only archives"
    assert not importlib.util.find_spec("datalab"), "datalab package must be fully removed"


def test_workshop_public_surface_remains_intact():
    """Spot-check a few helpers so the active namespace keeps working."""

    assert callable(workshop.get_lab_root)
    assert callable(workshop.data_path)
    lab_root = workshop.get_lab_root()
    assert (Path(lab_root) / "workshop").exists()


def test_workshop_modules_still_importable():
    """Importing Workshop submodules must continue to work even without legacy shims."""

    workshop_diag = importlib.import_module("workshop.diagnostics")
    workshop_lab_paths = importlib.import_module("workshop.lab_paths")
    workshop_widgets = importlib.import_module("workshop.widgets")

    assert hasattr(workshop_diag, "append_diagnostic_record")
    assert hasattr(workshop_lab_paths, "data_path")
    assert hasattr(workshop_widgets, "WidgetSpec")
