import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { elementsRegistry } from "../registry";
import { useGraphStore } from "../store/graphStore";
import { Surface, Stack } from "./primitives";
export const NodePalette = () => {
    const addNode = useGraphStore((state) => state.addNode);
    return (_jsx(Surface, { title: "Node palette", description: "Drag-and-drop free palette coming soon. Click to insert for now.", children: _jsx(Stack, { className: "elements-palette", children: elementsRegistry.all().map((definition) => (_jsxs("button", { type: "button", onClick: () => addNode(definition.type), children: [_jsxs("span", { style: { display: "flex", alignItems: "center", gap: "0.5rem" }, children: [_jsx("span", { "aria-hidden": true, children: definition.icon ?? "⬢" }), _jsx("strong", { children: definition.label })] }), _jsx("span", { style: { color: "#cbd5f5", fontSize: "0.8rem" }, children: definition.summary ?? "Reusable node" })] }, definition.type))) }) }));
};
