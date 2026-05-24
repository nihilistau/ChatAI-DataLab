import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NodePalette } from "./NodePalette";
import { GraphCanvas } from "./GraphCanvas";
import { GraphInspector } from "./GraphInspector";
import { Surface, Stack, MetricCard } from "./primitives";
import { useGraphStore } from "../store/graphStore";
import "../elements.css";
export const ElementsWorkbench = () => {
    const graph = useGraphStore((state) => state.graph);
    return (_jsxs(Stack, { gap: "1.5rem", children: [_jsx(Surface, { title: "Elements overview", description: "Shared schema between frontend, notebooks, and backend", children: _jsxs("div", { style: { display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }, children: [_jsx(MetricCard, { label: "Nodes", value: String(graph.nodes.length), hint: "In current graph" }), _jsx(MetricCard, { label: "Edges", value: String(graph.edges.length), hint: "Connections" }), _jsx(MetricCard, { label: "Workspace", value: graph.workspaceId, hint: "Tenant / workspace" })] }) }), _jsxs("div", { className: "elements-grid elements-grid--two-column", children: [_jsxs(Stack, { gap: "1rem", children: [_jsx(NodePalette, {}), _jsx(GraphInspector, {})] }), _jsx(Surface, { title: "Canvas", description: "React Flow powered draft of the Elements canvas", children: _jsx(GraphCanvas, {}) })] })] }));
};
