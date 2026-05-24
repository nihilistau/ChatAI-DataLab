from __future__ import annotations

"""Regression tests for workshop.widgets build_library."""

# @tag:workshop,tests,widgets

from workshop.widgets import build_library


def test_widget_library_shapes() -> None:
	"""Workshop widget collections should retain expected counts and samples."""

	library = build_library()

	assert len(library.telemetry) == 5
	assert len(library.control) == 5
	assert len(library.narrative) == 5
	assert len(library.panels) == 5
	assert len(library.pages) == 3

	snapshot = library.telemetry[0].as_dict()
	assert snapshot["title"] == "Latency Orbit"

	panel_md = library.panels[0].render_markdown()
	assert "Panel" in panel_md and "Ops Flight" in panel_md


def test_markdown_export_contains_sections() -> None:
	"""Markdown export should enumerate widget families for documentation."""

	md = build_library().to_markdown()
	assert "Telemetry widgets" in md
	assert "Page" in md
