import { WidgetSurface, MetricValue, ActionDock, Sparkline, StatusList } from "../design-system/WidgetPrimitives";

export function NotebookStudioPage() {
  return (
    <section>
      <div className="ds-page-hero">
        <p className="ds-eyebrow">Notebook studio</p>
        <h3>Canvas for experimental playbooks</h3>
        <p>Blend run telemetry with quick-launch macros for the notebooks powering the lab.</p>
      </div>
      <div className="ds-panel-grid">
        <WidgetSurface
          title="Notebook launchers"
          eyebrow="Pinned"
          accent="violet"
          description="Hand-curated bundles"
          dense
        >
          <ActionDock
            actions={[
              { label: "Control center", intent: "info" },
              { label: "Telemetry canvas", intent: "success" },
              { label: "Notebook drift map", intent: "warning" },
              { label: "Guardrail audit", intent: "danger" }
            ]}
          />
        </WidgetSurface>
        <WidgetSurface title="Run completion" eyebrow="24h" accent="forest" description="Success cadence">
          <MetricValue label="success" value="94%" delta="57 runs" />
          <Sparkline points={[60, 62, 68, 70, 75, 80, 88, 86, 92, 94]} stroke="#3ddad7" />
        </WidgetSurface>
        <WidgetSurface title="Kernel sentiment" eyebrow="Signals" accent="peach" description="How the ops team feels">
          <StatusList
            items={[
              { label: "Comfort", status: "High", tone: "success" },
              { label: "Focus", status: "Laser", tone: "info" },
              { label: "Fatigue", status: "Low", tone: "warning" }
            ]}
          />
        </WidgetSurface>
      </div>
    </section>
  );
}

export default NotebookStudioPage;
