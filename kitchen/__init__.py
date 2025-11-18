"""Kitchen helpers package.

All shared helpers now live under Kitchen so new code imports from here first.
``datalab`` provides thin compatibility shims that forward to these modules
until we fully retire that namespace.
"""

from .diagnostics import (
	DEFAULT_DIAGNOSTICS_LOG,
	DEFAULT_METADATA_PATH,
	DEFAULT_SNAPSHOT_PATH,
	append_diagnostic_record,
	get_default_paths,
	iter_diagnostic_records,
	record_run_metadata,
	write_snapshot,
)
from .lab_paths import (
	Pathish,
	data_path,
	describe_environment,
	ensure_directory,
	get_lab_root,
	iter_search_paths,
	lab_path,
	logs_path,
)
from .elements.schema import (
	ELEMENT_ID_PATTERN,
	ElementDefinition,
	ElementsCatalog,
	PortDefinition,
	RuntimeDefinition,
	find_element,
	iter_element_ids,
	load_catalog,
)
from .manifests import (
	ManifestValidationReport,
	PlaygroundManifestAction,
	PlaygroundManifestLayout,
	PlaygroundManifestModel,
	PlaygroundManifestRecordModel,
	PlaygroundManifestSection,
	PlaygroundManifestWidget,
	validate_manifest_payload,
)
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
	"ELEMENT_ID_PATTERN",
	"DEFAULT_DIAGNOSTICS_LOG",
	"DEFAULT_METADATA_PATH",
	"DEFAULT_SNAPSHOT_PATH",
	"append_diagnostic_record",
	"ManifestValidationReport",
	"ElementDefinition",
	"ElementsCatalog",
	"data_path",
	"describe_environment",
	"ensure_directory",
	"get_default_paths",
	"get_lab_root",
	"iter_search_paths",
	"iter_element_ids",
	"iter_diagnostic_records",
	"lab_path",
	"logs_path",
	"load_catalog",
	"record_run_metadata",
	"write_snapshot",
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
	"PortDefinition",
	"RuntimeDefinition",
	"find_element",
	"PlaygroundManifestAction",
	"PlaygroundManifestLayout",
	"PlaygroundManifestModel",
	"PlaygroundManifestRecordModel",
	"PlaygroundManifestSection",
	"PlaygroundManifestWidget",
	"validate_manifest_payload",
	"Pathish",
]
