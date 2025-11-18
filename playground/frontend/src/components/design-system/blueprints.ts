import { ReactNode, createElement } from "react";
import OpsGardenPage from "../pages/OpsGardenPage";
import NotebookStudioPage from "../pages/NotebookStudioPage";
import SignalWeatherPage from "../pages/SignalWeatherPage";

type Tone = "success" | "warning" | "info" | "danger" | "neutral";

export type PanelSegment = { label: string; value: string; tone?: Tone };

export type PanelBlueprint = {
  id: string;
  title: string;
  blurb: string;
  segments: PanelSegment[];
};

export type PageBlueprintPreview = {
  id: string;
  title: string;
  component: ReactNode;
  summary: string;
};

export type EscalationTimelineEntry = {
  window: string;
  panel: string;
  action: string;
};

export const panelBlueprints: PanelBlueprint[] = [
  {
    id: "ops-flight",
    title: "Ops flight panel",
    blurb: "Mini control center mixing latency and macros.",
    segments: [
      { label: "latency", value: "128 ms", tone: "info" },
      { label: "runs", value: "312", tone: "success" },
      { label: "alerts", value: "2", tone: "danger" }
    ]
  },
  {
    id: "notebook-flight",
    title: "Notebook flight panel",
    blurb: "Notebook throughput and comfort.",
    segments: [
      { label: "success", value: "94%", tone: "success" },
      { label: "median", value: "4m 32s", tone: "neutral" },
      { label: "reruns", value: "6", tone: "warning" }
    ]
  },
  {
    id: "signal-canvas",
    title: "Signal canvas",
    blurb: "Story-first telemetry.",
    segments: [
      { label: "positive", value: "+28%", tone: "success" },
      { label: "neutral", value: "61%", tone: "info" },
      { label: "negative", value: "11%", tone: "danger" }
    ]
  },
  {
    id: "guardrail-panel",
    title: "Guardrail sentinel",
    blurb: "Hits, pass rate, and macros.",
    segments: [
      { label: "pass", value: "86%", tone: "success" },
      { label: "mute", value: "4", tone: "warning" },
      { label: "critical", value: "0", tone: "danger" }
    ]
  },
  {
    id: "insights-panel",
    title: "Insights anthology",
    blurb: "Narrative + metric chips.",
    segments: [
      { label: "signals", value: "48", tone: "info" },
      { label: "insights", value: "12", tone: "success" },
      { label: "stories", value: "5", tone: "warning" }
    ]
  }
];

export const pageBlueprints: PageBlueprintPreview[] = [
  { id: "ops-garden", title: "Ops garden", component: createElement(OpsGardenPage), summary: "Cluster monitoring page" },
  { id: "notebook-studio", title: "Notebook studio", component: createElement(NotebookStudioPage), summary: "Creative lab" },
  { id: "signal-weather", title: "Signal weather", component: createElement(SignalWeatherPage), summary: "Executive weather" }
];

export const opsResponseBlueprint = {
  slug: "ops-response-playbook",
  title: "Ops Response Playbook",
  description: "Layout designed for command centers balancing action + storytelling.",
  panels: [
    {
      id: "stability-sweep",
      title: "Global Stability Sweep",
      purpose: "Consolidated anomalies + sparkline story across critical shards.",
      lane: "telemetry" as const
    },
    {
      id: "command-bridge",
      title: "Command Bridge",
      purpose: "Sequenced mitigations ready for runbook automation.",
      lane: "control" as const
    },
    {
      id: "narrative-feed",
      title: "Narrative Feed",
      purpose: "Single voice to broadcast context + next steps.",
      lane: "narrative" as const
    }
  ],
  escalationTimeline: [
    {
      window: "T+00",
      panel: "Global Stability Sweep",
      action: "Stitch anomaly review + sparkline commentary."
    },
    {
      window: "T+07",
      panel: "Command Bridge",
      action: "Sequence mitigations + trigger macros."
    },
    {
      window: "T+14",
      panel: "Narrative Feed",
      action: "Publish operator intent + async briefing."
    }
  ] as EscalationTimelineEntry[]
};
