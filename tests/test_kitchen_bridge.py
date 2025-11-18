"""Ensure the Kitchen namespace stands alone while legacy notebooks stay archived."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import kitchen

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_DATALAB = REPO_ROOT / "legacy" / "datalab"


def test_legacy_datalab_is_archived_only():
    """`legacy/datalab` should exist for historical notebook reference but not import."""

    assert LEGACY_DATALAB.exists(), "legacy/datalab should remain as read-only archives"
    assert not importlib.util.find_spec("datalab"), "datalab package must be fully removed"


def test_kitchen_public_surface_remains_intact():
    """Spot-check a few helpers so the active namespace keeps working."""

    assert callable(kitchen.get_lab_root)
    assert callable(kitchen.data_path)
    lab_root = kitchen.get_lab_root()
    assert (Path(lab_root) / "kitchen").exists()


def test_kitchen_modules_still_importable():
    """Importing Kitchen submodules must continue to work even without legacy shims."""

    kitchen_diag = importlib.import_module("kitchen.diagnostics")
    kitchen_lab_paths = importlib.import_module("kitchen.lab_paths")
    kitchen_widgets = importlib.import_module("kitchen.widgets")

    assert hasattr(kitchen_diag, "append_diagnostic_record")
    assert hasattr(kitchen_lab_paths, "data_path")
    assert hasattr(kitchen_widgets, "WidgetSpec")
