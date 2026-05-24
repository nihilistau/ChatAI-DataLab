import elementsCatalog from '../../../../elements.catalog.json';

export type ElementsCatalog = typeof elementsCatalog;
export type ElementDefinition = ElementsCatalog['elements'][number];

const ELEMENT_ID_PATTERN = /^[a-z0-9-]+@\d+\.\d+\.\d+$/;

export function isElementId(value: string): boolean {
	return ELEMENT_ID_PATTERN.test(value);
}

export function assertElementDefinition(definition: ElementDefinition): void {
	if (!isElementId(definition.id)) {
		throw new Error(`Invalid element id "${definition.id}". Expected type@major.minor.patch.`);
	}
	const expectedId = `${definition.type}@${definition.version}`;
	if (definition.id !== expectedId) {
		throw new Error(`Element id mismatch: got "${definition.id}" but expected "${expectedId}".`);
	}
}

export function getElementDefinition(id: string): ElementDefinition | undefined {
	return elementsCatalog.elements.find((definition) => definition.id === id);
}

export const ELEMENTS_CATALOG: ElementsCatalog = elementsCatalog;
