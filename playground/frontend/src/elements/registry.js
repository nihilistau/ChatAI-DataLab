class ElementsRegistry {
    constructor() {
        Object.defineProperty(this, "registry", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: {}
        });
    }
    register(definition) {
        this.registry[definition.type] = definition;
    }
    registerMany(definitions) {
        definitions.forEach((definition) => this.register(definition));
    }
    all() {
        return Object.values(this.registry);
    }
    get(type) {
        return this.registry[type];
    }
}
export const elementsRegistry = new ElementsRegistry();
