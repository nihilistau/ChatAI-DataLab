import { Fragment } from "react";
import { WidgetSurface, MetricValue, Sparkline, RadialGauge, StatusList, ActionDock } from "./WidgetPrimitives";
import { SECTION_TITLES } from "./DesignTokens";
import type { PanelBlueprint, PageBlueprintPreview } from "./blueprints";
import { panelBlueprints, pageBlueprints, opsResponseBlueprint } from "./blueprints";
import "./design-system.css";

type Example = {
  id: string;
  category: keyof typeof SECTION_TITLES;
  description: string;
  node: React.ReactNode;
};

const telemetryExamples: Example[] = [
  {
    id: "latency-orbit",
    category: "telemetry",
    description: "Latency orbit blends sparkline with delta context.",
    node: (
      <WidgetSurface title="Latency orbit" eyebrow="telemetry" accent="plasma" description="p95 ms" dense>
        <MetricValue label="milliseconds" value="118" delta="-12%" />
        <Sparkline points={[70, 62, 65, 60, 58, 61, 50, 48, 60, 55]} stroke="#15b8a6" />
      </WidgetSurface>
    )
  },
  {
    id: "ru-budget",
    category: "telemetry",
    description: "Budget gauge for RU envelope.",
    node: (
      <WidgetSurface title="RU budget" eyebrow="capacity" accent="lime" description="live">
        <RadialGauge value={72} label="consumed" />
      </WidgetSurface>
    )
  },
  {
    id: "model-uptime",
    category: "telemetry",
    description: "Status list summarizing uptime per region.",
    node: (
      <WidgetSurface title="Model uptime" eyebrow="regions" accent="cobalt" description="99.95 target">
        <StatusList
          items={[
            { label: "us-east", status: "99.98%", tone: "success" },
            { label: "eu-west", status: "99.92%", tone: "warning" },
            { label: "apac", status: "99.99%", tone: "info" }
          ]}
        />
      </WidgetSurface>
    )
  },
  {
    id: "token-consumption",
    category: "telemetry",
    description: "Token drift with gradient fill.",
    node: (
      <WidgetSurface title="Token drift" eyebrow="24h" accent="violet" description="per workspace">
        <Sparkline points={[35, 50, 62, 55, 60, 70, 74, 80, 78, 82]} stroke="#9d7bff" />
        <MetricValue label="avg tokens" value="1.3k" delta="+4%" />
      </WidgetSurface>
    )
  },
  {
    id: "guardrail-hits",
    category: "telemetry",
    description: "Guardrail map as bento list.",
    node: (
      <WidgetSurface title="Guardrail hits" eyebrow="hour" accent="ember" description="Top infra">
        <StatusList
          items={[
            { label: "Toxicity", status: "4", tone: "danger" },
            { label: "Prompt injection", status: "1", tone: "warning" },
            { label: "Secrets", status: "0", tone: "success" }
          ]}
        />
      </WidgetSurface>
    )
  }
];

const controlExamples: Example[] = [
  {
    id: "command-deck",
    category: "control",
    description: "Primary command buttons with tone coding.",
    node: (
      <WidgetSurface title="Command deck" eyebrow="ops" accent="forest" dense>
        <ActionDock
          actions={[
            { label: "restart api", intent: "danger" },
            { label: "scale notebooks", intent: "success" },
            { label: "sync telemetry", intent: "info" }
          ]}
        />
      </WidgetSurface>
    )
  },
  {
    id: "workflow-steppers",
    category: "control",
    description: "Sequential macro list.",
    node: (
      <WidgetSurface title="Workflow macro" eyebrow="canvas" accent="peach">
        <ol className="workflow-grid">
          <li>Snapshot control center</li>
          <li>Export signals</li>
          <li>Run guardrail audit</li>
        </ol>
      </WidgetSurface>
    )
  },
  {
    id: "theme-switch",
    category: "control",
    description: "Chips for theming.",
    node: (
      <WidgetSurface title="Theme switch" eyebrow="ui" accent="violet">
        <div className="ds-toolbar">
          <button type="button">midnight</button>
          <button type="button">forge</button>
          <button type="button">neon</button>
        </div>
      </WidgetSurface>
    )
  },
  {
    id: "notebook-launch",
    category: "control",
    description: "Notebook launcher grid.",
    node: (
      <WidgetSurface title="Notebook launch" eyebrow="studio" accent="plasma">
        <ActionDock
          actions={[
            { label: "RAG audit", intent: "info" },
            { label: "UX study", intent: "success" },
            { label: "Memory grid", intent: "warning" },
            { label: "Telemetry tilt", intent: "danger" }
          ]}
        />
      </WidgetSurface>
    )
  },
  {
    id: "ops-scenarios",
    category: "control",
    description: "Scenario toggles in list.",
    node: (
      <WidgetSurface title="Scenario toggles" eyebrow="ops" accent="lime">
        <StatusList
          items={[
            { label: "Chaos", status: "armed", tone: "warning" },
            { label: "Shadow traffic", status: "live", tone: "info" },
            { label: "Energy saver", status: "off", tone: "neutral" }
          ]}
        />
      </WidgetSurface>
    )
  }
];

const narrativeExamples: Example[] = [
  {
    id: "insight-card",
    category: "narrative",
    description: "Insight card with storyteller copy.",
    node: (
      <WidgetSurface title="Insight · Prompt rhythm" eyebrow="story" accent="peach" description="Cadence vs quality" dense>
        <p>
          Pauses clustered at 42% of total typing time correlate with the highest-rated prompts. Keep deliberate gaps before
          committing.
        </p>
      </WidgetSurface>
    )
  },
  {
    id: "persona-card",
    category: "narrative",
    description: "Persona tile for ops roles.",
    node: (
      <WidgetSurface title="Persona · Ops lead" eyebrow="people" accent="forest">
        <p>Prefers low-latency charts, wants guardrail heatmaps, and tunes macros nightly.</p>
      </WidgetSurface>
    )
  },
  {
    id: "signal-story",
    category: "narrative",
    description: "Signal story with highlight.",
    node: (
      <WidgetSurface title="Signal story" eyebrow="narrative" accent="violet">
        <p>
          Guardrail adoption jumped 18% once the neon toggles shipped in DataLab 2.1. Keep doubling down on immediate tactile
          feedback.
        </p>
      </WidgetSurface>
    )
  },
  {
    id: "win-log",
    category: "narrative",
    description: "Victory log.",
    node: (
      <WidgetSurface title="Win log" eyebrow="ops" accent="lime">
        <ul>
          <li>Reduced inference flakiness from 0.9% to 0.1%.</li>
          <li>Launched guardrail composer.</li>
          <li>Storybook parity with Ops drift.</li>
        </ul>
      </WidgetSurface>
    )
  },
  {
    id: "design-principles",
    category: "narrative",
    description: "Design rubric.",
    node: (
      <WidgetSurface title="Design principles" eyebrow="system" accent="cobalt">
        <ul>
          <li>High-contrast glass with purposeful glow.</li>
          <li>Segmented panels showing intent.</li>
          <li>Navigation anchored to mission copy.</li>
        </ul>
      </WidgetSurface>
    )
  }
];

function PanelPreview({ panel }: { panel: PanelBlueprint }) {
  return (
    <article className="ds-widget" style={{ minHeight: "auto" }}>
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
  );
}

function BlueprintTimeline() {
  return (
    <div className="ds-blueprint-stack">
      <article className="ds-widget ds-blueprint-callout">
        <p className="ds-eyebrow">Ops blueprint</p>
        <h3>{opsResponseBlueprint.title}</h3>
        <p>{opsResponseBlueprint.description}</p>
        <div className="ds-chip-row">
          {opsResponseBlueprint.panels.map((panel) => (
            <span key={panel.id} className="ds-chip">
              {panel.lane} · {panel.title}
            </span>
          ))}
        </div>
      </article>
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
    </div>
  );
}

export function WidgetShowcase() {
  const grouped: Record<string, Example[]> = {
    telemetry: telemetryExamples,
    control: controlExamples,
    narrative: narrativeExamples
  };

  return (
    <section className="widget-showcase">
      <div className="section-head">
        <div>
          <p className="ds-eyebrow">Design system</p>
          <h2>Widget + panel library</h2>
        </div>
        <p>
          Advanced components built specifically for ChatAI · DataLab—telemetry gauges, neon command docks, narrative tiles, and
          full-page layouts ready for production wiring.
        </p>
      </div>

      {Object.entries(grouped).map(([category, examples]) => (
        <Fragment key={category}>
          <header className="section-head">
            <h3>{SECTION_TITLES[category as keyof typeof SECTION_TITLES]}</h3>
            <p>Five ready-to-wire specimens for the {category} stream.</p>
          </header>
          <div className="ds-grid">
            {examples.map((example) => (
              <div key={example.id}>{example.node}</div>
            ))}
          </div>
        </Fragment>
      ))}

      <header className="section-head">
        <h3>Panels in action</h3>
        <p>Five composable panels mixing widgets into actionable glass.</p>
      </header>
      <div className="ds-panel-grid">
        {panelBlueprints.map((panel) => (
          <PanelPreview key={panel.id} panel={panel} />
        ))}
      </div>

      <header className="section-head">
        <h3>Page blueprints</h3>
        <p>Three full-stack experiences ready to drop into routing.</p>
      </header>
      <div className="ds-page-gallery">
        {pageBlueprints.map((page: PageBlueprintPreview) => (
          <div key={page.id} className="ds-page-frame">
            <h3>{page.title}</h3>
            <p>{page.summary}</p>
            {page.component}
          </div>
        ))}
      </div>

      <header className="section-head">
        <h3>Ops escalation timeline</h3>
        <p>
          This stream mirrors the advanced notebook&#39;s timeline output so design + ops can collaborate inside Storybook or the
          showcase without running Python first.
        </p>
      </header>
      <BlueprintTimeline />
    </section>
  );
}

export default WidgetShowcase;
