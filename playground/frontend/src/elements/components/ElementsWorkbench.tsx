import React from "react";
import { NodePalette } from "./NodePalette";
import { GraphCanvas } from "./GraphCanvas";
import { GraphInspector } from "./GraphInspector";
import { Surface, Stack, MetricCard } from "./primitives";
import { useGraphStore } from "../store/graphStore";
import "../elements.css";

export const ElementsWorkbench: React.FC = () => {
  const graph = useGraphStore((state) => state.graph);

  return (
    <Stack gap="1.5rem">
      <Surface title="Elements overview" description="Shared schema between frontend, notebooks, and backend">
        <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <MetricCard label="Nodes" value={String(graph.nodes.length)} hint="In current graph" />
          <MetricCard label="Edges" value={String(graph.edges.length)} hint="Connections" />
          <MetricCard label="Workspace" value={graph.workspaceId} hint="Tenant / workspace" />
        </div>
      </Surface>
      <div className="elements-grid elements-grid--two-column">
        <Stack gap="1rem">
          <NodePalette />
          <GraphInspector />
        </Stack>
        <Surface title="Canvas" description="React Flow powered draft of the Elements canvas">
          <GraphCanvas />
        </Surface>
      </div>
    </Stack>
  );
};
