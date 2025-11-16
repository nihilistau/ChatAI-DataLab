import { WidgetSurface, MetricValue, Sparkline, ActionDock, StatusList } from "../design-system/WidgetPrimitives";

export function OpsGardenPage() {
  return (
    <section>
      <div className="ds-page-hero">
        <p className="ds-eyebrow">Ops garden</p>
        <h3>Multi-cluster observability lattice</h3>
        <p>Live runway for the on-call lead—latency spark, command dock, and drift watch within one page.</p>
      </div>
      <div className="ds-panel-grid">
        <WidgetSurface title="Latency envelope" eyebrow="SLO" accent="plasma" description="p95 across inference pods">
          <MetricValue label="milliseconds" value="128" delta="-23% vs 24h" />
          <Sparkline points={[70, 80, 65, 55, 60, 50, 45, 52, 40, 42]} stroke="#5df4ff" />
        </WidgetSurface>
        <WidgetSurface title="Command runway" eyebrow="Ops" accent="lime" description="Favorite macros">
          <ActionDock
            actions={[
              { label: "roll restart", intent: "info" },
              { label: "scale inference", intent: "success" },
              { label: "purge cache", intent: "warning" }
            ]}
          />
        </WidgetSurface>
        <WidgetSurface title="Drift sentry" eyebrow="Signals" accent="ember" description="Top regressions">
          <StatusList
            items={[
              { label: "Search preset", status: "+8% density", tone: "warning" },
              { label: "Notebook runtime", status: "stable", tone: "info" },
              { label: "Guardrail hits", status: "down 12%", tone: "success" }
            ]}
          />
        </WidgetSurface>
      </div>
    </section>
  );
}

export default OpsGardenPage;
