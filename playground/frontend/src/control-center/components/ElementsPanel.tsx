import React from "react";
import { ElementsWorkbench } from "../../elements";

export const ElementsPanel: React.FC = () => (
  <section className="control-card">
    <header className="control-card__header">
      <div>
        <p style={{ margin: 0, color: "var(--control-muted)", textTransform: "uppercase", fontSize: "0.85rem" }}>Elements</p>
        <h2 style={{ margin: 0 }}>Node builder preview</h2>
        <span style={{ color: "var(--control-muted)", fontSize: "0.85rem" }}>
          Draft implementation of the Elements canvas powered by the shared widget registry.
        </span>
      </div>
    </header>
    <ElementsWorkbench />
  </section>
);
