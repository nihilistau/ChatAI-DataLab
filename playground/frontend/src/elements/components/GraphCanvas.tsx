import React, { useMemo, useCallback } from "react";
import { ReactFlow, MiniMap, Controls, Background, Connection, NodeChange, applyNodeChanges, Edge, Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useGraphStore } from "../store/graphStore";
import { GraphDefinition, GraphEdge } from "../types";
import { elementsRegistry } from "../registry";

const toReactFlowNodes = (nodes: GraphDefinition["nodes"]): Node[] =>
  nodes.map((node) => ({
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

const toReactFlowEdges = (edges: GraphEdge[]): Edge[] =>
  edges.map((edge) => ({
    id: edge.id,
    source: edge.from.node,
    target: edge.to.node,
    animated: true,
    label: `${edge.from.port} → ${edge.to.port}`,
    style: { stroke: "#38bdf8" }
  }));

export const GraphCanvas: React.FC = () => {
  const graph = useGraphStore((state) => state.graph);
  const updateNodePosition = useGraphStore((state) => state.updateNodePosition);
  const connectNodes = useGraphStore((state) => state.connectNodes);
  const selectNode = useGraphStore((state) => state.selectNode);

  const nodes = useMemo(() => toReactFlowNodes(graph.nodes), [graph.nodes]);
  const edges = useMemo(() => toReactFlowEdges(graph.edges), [graph.edges]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const updated = applyNodeChanges(changes, nodes);
      updated.forEach((node) => updateNodePosition(node.id, node.position));
    },
    [nodes, updateNodePosition]
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      const findPort = (nodeId: string, direction: "in" | "out") => {
        const node = graph.nodes.find((candidate) => candidate.id === nodeId);
        if (!node) return direction;
        const definition = elementsRegistry.get(node.type);
        const ports = definition ? (direction === "out" ? definition.outputs : definition.inputs) : undefined;
        const fallback = Object.keys(ports ?? {})[0] ?? direction;
        return direction === "out" ? connection.sourceHandle ?? fallback : connection.targetHandle ?? fallback;
      };
      connectNodes(
        { node: connection.source, port: findPort(connection.source, "out") },
        { node: connection.target, port: findPort(connection.target, "in") }
      );
    },
    [connectNodes, graph.nodes]
  );

  return (
    <div className="elements-canvas-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onConnect={handleConnect}
        onNodeClick={(_, node) => selectNode(node.id)}
        fitView
      >
        <MiniMap pannable zoomable />
        <Controls showInteractive={false} />
        <Background gap={22} size={2} />
      </ReactFlow>
    </div>
  );
};
