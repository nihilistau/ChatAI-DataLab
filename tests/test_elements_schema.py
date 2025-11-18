from pathlib import Path

from kitchen.elements.schema import (
	ELEMENT_ID_PATTERN,
	ElementDefinition,
	ElementsCatalog,
	find_element,
	iter_element_ids,
	load_catalog,
)


def test_catalog_loads_and_matches_schema(tmp_path: Path) -> None:
	catalog = load_catalog()
	assert isinstance(catalog, ElementsCatalog)
	assert catalog.catalog_version.count(".") == 2
	assert catalog.elements, "Catalog should contain at least one element definition."
	for definition in catalog.elements:
		assert isinstance(definition, ElementDefinition)
		assert definition.id == f"{definition.type}@{definition.version}"
		assert ELEMENT_ID_PATTERN.match(definition.id)


def test_find_element_and_iteration() -> None:
	prompt = find_element("prompt@1.0.0")
	assert prompt is not None
	assert prompt.outputs
	ids = iter_element_ids()
	assert "prompt@1.0.0" in ids
	assert all(ELEMENT_ID_PATTERN.match(element_id) for element_id in ids)
