import React from "react";
import { elementsRegistry } from "../registry";
import { useGraphStore } from "../store/graphStore";
import { Surface, Stack } from "./primitives";
import { ElementPropertySchema } from "../types";

export const GraphInspector: React.FC = () => {
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  const node = useGraphStore((state) => state.graph.nodes.find((n) => n.id === state.selectedNodeId));
  const updateProps = useGraphStore((state) => state.updateNodeProps);

  if (!selectedNodeId || !node) {
    return (
      <Surface title="Inspector" description="Select a node to see its parameters.">
        <p style={{ color: "#94a3b8" }}>No node selected.</p>
      </Surface>
    );
  }

  const definition = elementsRegistry.get(node.type);

  return (
    <Surface title={`Inspector • ${node.label}`} description={definition?.summary}>
      <Stack className="elements-inspector">
        {definition ? (
          Object.entries(definition.propsSchema as Record<string, ElementPropertySchema>).map(([key, schema]) => {
            const value = (node.props[key] ?? schema.default ?? "") as string | number;
            const isNumber = schema.type === "number";
            const isTextArea = schema.widget === "textarea";
            const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
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
              return (
                <label key={key}>
                  {key}
                  <select {...inputProps}>
                    {schema.enum.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              );
            }

            if (isNumber) {
              return (
                <label key={key}>
                  {key}
                  <input type="number" step="0.1" {...inputProps} />
                </label>
              );
            }

            if (isTextArea) {
              return (
                <label key={key}>
                  {key}
                  <textarea rows={3} {...inputProps} />
                </label>
              );
            }

            return (
              <label key={key}>
                {key}
                <input type="text" {...inputProps} />
              </label>
            );
          })
        ) : (
          <p style={{ color: "#94a3b8" }}>No schema for node type &quot;{node.type}&quot;.</p>
        )}
      </Stack>
    </Surface>
  );
};
