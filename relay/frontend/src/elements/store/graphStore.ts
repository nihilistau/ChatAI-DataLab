import { create } from "zustand";
import { nanoid } from "nanoid";
import { GraphDefinition, NodeInstance, GraphEdge } from "../types";
import { defaultGraph } from "../presets";
import { elementsRegistry } from "../registry";
import { builtInNodes } from "../nodes";

elementsRegistry.registerMany(builtInNodes);

interface GraphState {
  graph: GraphDefinition;
  selectedNodeId: string | null;
  setGraph: (graph: GraphDefinition) => void;
  selectNode: (nodeId: string | null) => void;
  addNode: (type: string) => void;
  updateNodeProps: (nodeId: string, props: Record<string, unknown>) => void;
  updateNodePosition: (nodeId: string, position: NodeInstance["position"]) => void;
  connectNodes: (from: GraphEdge["from"], to: GraphEdge["to"]) => void;
  deleteNode: (nodeId: string) => void;
}

const withNewGraph = (graph: GraphDefinition): GraphDefinition => ({
  ...graph,
  nodes: [...graph.nodes],
  edges: [...graph.edges]
});

export const useGraphStore = create<GraphState>((set, get) => ({
  graph: withNewGraph(defaultGraph),
  selectedNodeId: defaultGraph.nodes[0]?.id ?? null,
  setGraph: (graph) => set({ graph: withNewGraph(graph) }),
  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),
  addNode: (type) => {
    const definition = elementsRegistry.get(type);
    if (!definition) return;
    const newNode: NodeInstance = {
      id: nanoid(6),
      type,
      label: definition.label,
      props: {},
      position: { x: 120 + Math.random() * 320, y: 120 + Math.random() * 320 }
    };
    set(({ graph }) => ({ graph: { ...graph, nodes: [...graph.nodes, newNode] }, selectedNodeId: newNode.id }));
  },
  updateNodeProps: (nodeId, props) =>
    set(({ graph }) => ({
      graph: {
        ...graph,
        nodes: graph.nodes.map((node) => (node.id === nodeId ? { ...node, props: { ...node.props, ...props } } : node))
      }
    })),
  updateNodePosition: (nodeId, position) =>
    set(({ graph }) => ({
      graph: {
        ...graph,
        nodes: graph.nodes.map((node) => (node.id === nodeId ? { ...node, position } : node))
      }
    })),
  connectNodes: (from, to) => {
    const edgeId = nanoid(6);
    set(({ graph }) => ({ graph: { ...graph, edges: [...graph.edges, { id: edgeId, from, to }] } }));
  },
  deleteNode: (nodeId) =>
    set(({ graph }) => ({
      graph: {
        ...graph,
        nodes: graph.nodes.filter((node) => node.id !== nodeId),
        edges: graph.edges.filter((edge) => edge.from.node !== nodeId && edge.to.node !== nodeId)
      },
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId
    }))
}));
