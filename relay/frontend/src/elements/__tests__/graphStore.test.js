import { act } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useGraphStore } from "../store/graphStore";
import { defaultGraph } from "../presets";
describe("graph store", () => {
    afterEach(() => {
        act(() => {
            useGraphStore.getState().setGraph(defaultGraph);
            useGraphStore.getState().selectNode(defaultGraph.nodes[0]?.id ?? null);
        });
    });
    it("adds nodes via palette", () => {
        const before = useGraphStore.getState().graph.nodes.length;
        act(() => useGraphStore.getState().addNode("prompt"));
        const after = useGraphStore.getState().graph.nodes.length;
        expect(after).toBe(before + 1);
    });
    it("connects nodes", () => {
        const [first, second] = useGraphStore.getState().graph.nodes;
        act(() => useGraphStore
            .getState()
            .connectNodes({ node: first.id, port: "text" }, { node: second.id, port: "prompt" }));
        const edges = useGraphStore.getState().graph.edges;
        expect(edges.at(-1)).toMatchObject({ from: { node: first.id }, to: { node: second.id } });
    });
});
