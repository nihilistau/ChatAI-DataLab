from __future__ import annotations

"""Regression tests for DataLab widget library."""

from datalab.widgets import build_library


def test_widget_library_shapes() -> None:
    library = build_library()
    assert len(library.telemetry) == 5
    assert len(library.control) == 5
    assert len(library.narrative) == 5
    assert len(library.panels) == 5
    assert len(library.pages) == 3

    snapshot = library.telemetry[0].as_dict()
    assert snapshot["title"] == "Latency Orbit"
    md = library.panels[0].render_markdown()
    assert "Panel" in md and "Ops Flight" in md


def test_markdown_export_contains_sections() -> None:
    md = build_library().to_markdown()
    assert "Telemetry widgets" in md
    assert "Page" in md
