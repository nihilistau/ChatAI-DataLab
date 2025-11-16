"""DataLab helpers package for analytics scripts and notebooks."""
# @tag: datalab,package

from .lab_paths import data_path, get_lab_root, lab_path, logs_path
from .diagnostics import append_diagnostic_record, record_run_metadata
from .widgets import (
	PageBlueprint,
	PanelSpec,
	WidgetLibrary,
	WidgetSpec,
	blueprint_pages,
	build_library,
	control_widgets,
	narrative_widgets,
	showcase_panels,
	telemetry_widgets,
)

__all__ = [
	"append_diagnostic_record",
	"data_path",
	"get_lab_root",
	"lab_path",
	"logs_path",
	"record_run_metadata",
	"WidgetSpec",
	"PanelSpec",
	"PageBlueprint",
	"WidgetLibrary",
	"telemetry_widgets",
	"control_widgets",
	"narrative_widgets",
	"showcase_panels",
	"blueprint_pages",
	"build_library",
]
