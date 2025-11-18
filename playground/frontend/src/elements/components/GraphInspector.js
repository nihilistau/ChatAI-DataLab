import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { elementsRegistry } from "../registry";
import { useGraphStore } from "../store/graphStore";
import { Surface, Stack } from "./primitives";
export const GraphInspector = () => {
    const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
    const node = useGraphStore((state) => state.graph.nodes.find((n) => n.id === state.selectedNodeId));
    const updateProps = useGraphStore((state) => state.updateNodeProps);
    if (!selectedNodeId || !node) {
        return (_jsx(Surface, { title: "Inspector", description: "Select a node to see its parameters.", children: _jsx("p", { style: { color: "#94a3b8" }, children: "No node selected." }) }));
    }
    const definition = elementsRegistry.get(node.type);
    return (_jsx(Surface, { title: `Inspector • ${node.label}`, description: definition?.summary, children: _jsx(Stack, { className: "elements-inspector", children: definition ? (Object.entries(definition.propsSchema).map(([key, schema]) => {
                const value = (node.props[key] ?? schema.default ?? "");
                const isNumber = schema.type === "number";
                const isTextArea = schema.widget === "textarea";
                const handleChange = (event) => {
                    const raw = event.target.value;
                    const nextValue = isNumber ? Number(raw) : raw;
                    updateProps(node.id, { [key]: nextValue });
                };
                const inputProps = {
                    name: key,
                    value,
                    onChange: handleChange
                };
                if (schema.enum) {
                    return (_jsxs("label", { children: [key, _jsx("select", { ...inputProps, children: schema.enum.map((option) => (_jsx("option", { value: option, children: option }, option))) })] }, key));
                }
                if (isNumber) {
                    return (_jsxs("label", { children: [key, _jsx("input", { type: "number", step: "0.1", ...inputProps })] }, key));
                }
                if (isTextArea) {
                    return (_jsxs("label", { children: [key, _jsx("textarea", { rows: 3, ...inputProps })] }, key));
                }
                return (_jsxs("label", { children: [key, _jsx("input", { type: "text", ...inputProps })] }, key));
            })) : (_jsxs("p", { style: { color: "#94a3b8" }, children: ["No schema for node type \"", node.type, "\"."] })) }) }));
};
