import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useCallback } from "react";
import { ReactFlow, MiniMap, Controls, Background, applyNodeChanges } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useGraphStore } from "../store/graphStore";
import { elementsRegistry } from "../registry";
const toReactFlowNodes = (nodes) => nodes.map((node) => ({
    id: node.id,
    position: node.position,
    data: { label: node.label, type: node.type },
    style: {
        padding: "0.5rem 0.75rem",
        borderRadius: 10,
        border: "1px solid rgba(56,189,248,0.4)",
        background: "rgba(56, 189, 248, 0.12)",
        color: "#e0f2fe"
    }
}));
const toReactFlowEdges = (edges) => edges.map((edge) => ({
    id: edge.id,
    source: edge.from.node,
    target: edge.to.node,
    animated: true,
    label: `${edge.from.port} → ${edge.to.port}`,
    style: { stroke: "#38bdf8" }
}));
export const GraphCanvas = () => {
    const graph = useGraphStore((state) => state.graph);
    const updateNodePosition = useGraphStore((state) => state.updateNodePosition);
    const connectNodes = useGraphStore((state) => state.connectNodes);
    const selectNode = useGraphStore((state) => state.selectNode);
    const nodes = useMemo(() => toReactFlowNodes(graph.nodes), [graph.nodes]);
    const edges = useMemo(() => toReactFlowEdges(graph.edges), [graph.edges]);
    const handleNodesChange = useCallback((changes) => {
        const updated = applyNodeChanges(changes, nodes);
        updated.forEach((node) => updateNodePosition(node.id, node.position));
    }, [nodes, updateNodePosition]);
    const handleConnect = useCallback((connection) => {
        if (!connection.source || !connection.target)
            return;
        const findPort = (nodeId, direction) => {
            const node = graph.nodes.find((candidate) => candidate.id === nodeId);
            if (!node)
                return direction;
            const definition = elementsRegistry.get(node.type);
            const ports = definition ? (direction === "out" ? definition.outputs : definition.inputs) : undefined;
            const fallback = Object.keys(ports ?? {})[0] ?? direction;
            return direction === "out" ? connection.sourceHandle ?? fallback : connection.targetHandle ?? fallback;
        };
        connectNodes({ node: connection.source, port: findPort(connection.source, "out") }, { node: connection.target, port: findPort(connection.target, "in") });
    }, [connectNodes, graph.nodes]);
    return (_jsx("div", { className: "elements-canvas-wrapper", children: _jsxs(ReactFlow, { nodes: nodes, edges: edges, onNodesChange: handleNodesChange, onConnect: handleConnect, onNodeClick: (_, node) => selectNode(node.id), fitView: true, children: [_jsx(MiniMap, { pannable: true, zoomable: true }), _jsx(Controls, { showInteractive: false }), _jsx(Background, { gap: 22, size: 2 })] }) }));
};
