import type { Meta, StoryObj } from "@storybook/react";
import { panelBlueprints, pageBlueprints, opsResponseBlueprint } from "./blueprints";
import "./design-system.css";

function BlueprintLibrary() {
  return (
    <section className="widget-showcase" style={{ marginTop: 0 }}>
      <div className="section-head">
        <div>
          <p className="ds-eyebrow">Blueprint exports</p>
          <h2>Panel + page artifacts</h2>
        </div>
        <p>
          These blueprints mirror the Python/DataLab exports, so Storybook consumers can review panel segments and the Ops
          Response timeline without leaving the UI stack.
        </p>
      </div>

      <header className="section-head">
        <h3>Panels</h3>
        <p>Segment data for each reusable panel.</p>
      </header>
      <div className="ds-panel-grid">
        {panelBlueprints.map((panel) => (
          <article key={panel.id} className="ds-widget" style={{ minHeight: "auto" }}>
            <h3>{panel.title}</h3>
            <p>{panel.blurb}</p>
            <div className="ds-bento">
              {panel.segments.map((segment) => (
                <div key={segment.label}>
                  <small className="ds-metric-caption">{segment.label}</small>
                  <strong>{segment.value}</strong>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>

      <header className="section-head">
        <h3>Page blueprints</h3>
        <p>Live React previews for each exported layout.</p>
      </header>
      <div className="ds-page-gallery">
        {pageBlueprints.map((page) => (
          <div key={page.id} className="ds-page-frame">
            <h3>{page.title}</h3>
            <p>{page.summary}</p>
            {page.component}
          </div>
        ))}
      </div>

      <header className="section-head">
        <h3>Ops Response timeline</h3>
        <p>{opsResponseBlueprint.description}</p>
      </header>
      <ol className="ds-timeline">
        {opsResponseBlueprint.escalationTimeline.map((entry) => (
          <li key={entry.window}>
            <span className="ds-timeline-window">{entry.window}</span>
            <div>
              <strong>{entry.panel}</strong>
              <p>{entry.action}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

const meta: Meta<typeof BlueprintLibrary> = {
  title: "Design System/Blueprint Library",
  component: BlueprintLibrary
};

export default meta;

type Story = StoryObj<typeof BlueprintLibrary>;

export const Overview: Story = {
  render: () => <BlueprintLibrary />
};
