import { elementsRegistry } from "../registry";
import { builtInNodes } from "../nodes";

describe("elements registry", () => {
  beforeAll(() => {
    elementsRegistry.registerMany(builtInNodes);
  });

  it("exposes built-in node types", () => {
    const types = elementsRegistry.all().map((node) => node.type);
    expect(types).toEqual(expect.arrayContaining(["prompt", "llm", "notebook"]));
  });

  it("returns the latest definition", () => {
    elementsRegistry.register({
      ...builtInNodes[0],
      version: "2.0.0",
      summary: "Updated"
    });

    const definition = elementsRegistry.get("prompt");
    expect(definition?.version).toBe("2.0.0");
  });
});
