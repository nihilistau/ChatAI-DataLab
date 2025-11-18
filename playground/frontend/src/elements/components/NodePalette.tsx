import React from "react";
import { elementsRegistry } from "../registry";
import { useGraphStore } from "../store/graphStore";
import { Surface, Stack } from "./primitives";

export const NodePalette: React.FC = () => {
  const addNode = useGraphStore((state) => state.addNode);

  return (
    <Surface title="Node palette" description="Drag-and-drop free palette coming soon. Click to insert for now.">
      <Stack className="elements-palette">
        {elementsRegistry.all().map((definition) => (
          <button key={definition.type} type="button" onClick={() => addNode(definition.type)}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span aria-hidden>{definition.icon ?? "⬢"}</span>
              <strong>{definition.label}</strong>
            </span>
            <span style={{ color: "#cbd5f5", fontSize: "0.8rem" }}>{definition.summary ?? "Reusable node"}</span>
          </button>
        ))}
      </Stack>
    </Surface>
  );
};
