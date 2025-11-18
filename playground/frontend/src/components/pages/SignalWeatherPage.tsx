import { WidgetSurface, MetricValue, Sparkline, RadialGauge, StatusList } from "../design-system/WidgetPrimitives";

export function SignalWeatherPage() {
  return (
    <section>
      <div className="ds-page-hero">
        <p className="ds-eyebrow">Signal weather</p>
        <h3>Global situational awareness</h3>
        <p>Styled snapshot fusing user behavior analytics, run guardrails, and anomaly beacons.</p>
      </div>
      <div className="ds-panel-grid">
        <WidgetSurface title="Guardrail health" eyebrow="Realtime" accent="lime" description="Across tenants">
          <RadialGauge value={86} label="Pass rate" />
        </WidgetSurface>
        <WidgetSurface title="Anomaly spikes" eyebrow="Signals" accent="cobalt" description="AI sensemaking">
          <Sparkline points={[10, 14, 12, 20, 32, 18, 25, 15, 10, 8]} stroke="#7e9dff" />
          <MetricValue label="alerts" value="7" delta="3 muted" />
        </WidgetSurface>
        <WidgetSurface title="User cohorts" eyebrow="Blended" accent="ember" description="Engagement arc">
          <StatusList
            items={[
              { label: "Builders", status: "+42% time on canvas", tone: "success" },
              { label: "Analysts", status: "+12% queries", tone: "info" },
              { label: "Execs", status: "stable", tone: "neutral" }
            ]}
          />
        </WidgetSurface>
      </div>
    </section>
  );
}

export default SignalWeatherPage;
