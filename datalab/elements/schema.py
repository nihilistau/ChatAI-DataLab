from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "elements.catalog.json"
ELEMENT_ID_PATTERN = re.compile(r"^[a-z0-9-]+@\d+\.\d+\.\d+$")


class PortDefinition(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	label: str
	description: str | None = None
	data_type: str = Field(..., alias="dataType")
	required: bool = False


class RuntimeDefinition(BaseModel):
	executor: str
	handler: str


class ElementDefinition(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: str
	type: str
	version: str
	label: str
	icon: str | None = None
	category: str | None = None
	inputs: dict[str, PortDefinition]
	outputs: dict[str, PortDefinition]
	props_schema: dict[str, Any] = Field(..., alias="propsSchema")
	runtime: RuntimeDefinition
	metadata: dict[str, Any] | None = None

	@field_validator("id")
	@classmethod
	def validate_identifier(cls, value: str, info: ValidationInfo) -> str:  # type: ignore[override]
		if not ELEMENT_ID_PATTERN.match(value):
			raise ValueError(
				f"Invalid element id '{value}'. Expected format type@major.minor.patch."
			)
		type_value = info.data.get("type")
		version_value = info.data.get("version")
		if type_value and version_value and value != f"{type_value}@{version_value}":
			raise ValueError(
				f"Element id '{value}' mismatches type '{type_value}' and version '{version_value}'."
			)
		return value


class ElementsCatalog(BaseModel):
	catalog_version: str = Field(..., alias="catalogVersion")
	elements: list[ElementDefinition]


@lru_cache(maxsize=1)
def load_catalog(path: Path | None = None) -> ElementsCatalog:
	"""Load and validate the shared elements schema catalog."""

	catalog_path = Path(path) if path else CATALOG_PATH
	with catalog_path.open("r", encoding="utf-8") as handle:
		payload = json.load(handle)
	return ElementsCatalog.model_validate(payload)


def find_element(element_id: str, *, path: Path | None = None) -> ElementDefinition | None:
	"""Return the element definition for the provided id, if present."""

	catalog = load_catalog(path)
	return next((element for element in catalog.elements if element.id == element_id), None)


def iter_element_ids(*, path: Path | None = None) -> list[str]:
	"""Return a sorted list of registered element identifiers."""

	catalog = load_catalog(path)
	return sorted(element.id for element in catalog.elements)


__all__ = [
	"ElementsCatalog",
	"ElementDefinition",
	"PortDefinition",
	"RuntimeDefinition",
	"find_element",
	"iter_element_ids",
	"load_catalog",
	"ELEMENT_ID_PATTERN",
]
