import { ElementsRegistryMap, ElementDefinition } from "./types";

class ElementsRegistry {
  private registry: ElementsRegistryMap = {};

  register(definition: ElementDefinition) {
    this.registry[definition.type] = definition;
  }

  registerMany(definitions: ElementDefinition[]) {
    definitions.forEach((definition) => this.register(definition));
  }

  all(): ElementDefinition[] {
    return Object.values(this.registry);
  }

  get(type: string) {
    return this.registry[type];
  }
}

export const elementsRegistry = new ElementsRegistry();
