import type {
  PlaygroundAction,
  PlaygroundLayoutSection,
  PlaygroundManifestRecord
} from "../types";

export interface ManifestStoryKnobs {
  tenant: string;
  playground: string;
  revision: number;
  revisionLabel: string;
  cookbook: string;
  recipe: string;
  author: string;
  notes: string;
  metadata: Record<string, unknown>;
  sections: PlaygroundLayoutSection[];
  actions: PlaygroundAction[];
}

const baseCreatedAt = Date.now() - 1000 * 60 * 60;

const defaultSections: PlaygroundLayoutSection[] = [
  {
    id: "intel",
    title: "Intel stack",
    description: "At-a-glance metrics sourced from RU burn and telemetry lanes.",
    widgets: [
      {
        id: "ru-burn",
        type: "stat-card",
        title: "RU burn",
        props: { label: "Avg RU/s", value: 48, trend: "down" }
      },
      {
        id: "latency",
        type: "stat-card",
        title: "LLM latency",
        props: { label: "p95 latency", value: "820 ms" }
      }
    ]
  },
  {
    id: "actions",
    title: "Automation",
    description: "Trigger Ops or Kitchen routines wired to manifest actions.",
    widgets: [
      {
        id: "notebook",
        type: "notebook-trigger",
        title: "Run control_center_playground",
        props: {
          label: "Notebook",
          notebook: "control_center_playground.ipynb",
          placeholder: "Parameters JSON"
        }
      },
      {
        id: "search-refresh",
        type: "workflow",
        title: "Search telemetry refresh",
        props: {
          label: "Refresh",
          confirmation: "Kick notebook + pipeline"
        }
      }
    ]
  }
];

const defaultActions: PlaygroundAction[] = [
  {
    id: "deploy-control",
    title: "Deploy Control Center",
    method: "POST",
    route: "/api/control/deploy",
    description: "Runs the orchestrator capsule and syncs notebooks."
  },
  {
    id: "refresh-search",
    title: "Refresh search telemetry",
    method: "POST",
    route: "/api/search/refresh",
    description: "Recomputes drift metrics before design review."
  }
];

export const defaultManifestKnobs: ManifestStoryKnobs = {
  tenant: "demo-tenant",
  playground: "welcome-control",
  revision: 3,
  revisionLabel: "ops-demo",
  cookbook: "Welcome Cookbook",
  recipe: "control_center_playground",
  author: "Ops Kitchen",
  notes: "Manifest published from the Welcome Cookbook run.",
  metadata: {
    hero: "Kitchen publishes manifest revisions that hydrate the Control Center shell.",
    notes: "Adjust widget mix to match the telemetry lanes under review.",
    tags: ["ops", "manifest", "kitchen"]
  },
  sections: defaultSections,
  actions: defaultActions
};

const cloneSections = (sections: PlaygroundLayoutSection[]): PlaygroundLayoutSection[] =>
  sections.map((section, sectionIndex) => ({
    ...section,
    id: section.id ?? `section-${sectionIndex}`,
    widgets: (section.widgets ?? []).map((widget, widgetIndex) => ({
      ...widget,
      id: widget.id ?? `${widget.type}-${widgetIndex}`,
      props: widget.props ? { ...widget.props } : undefined
    }))
  }));

const cloneActions = (actions: PlaygroundAction[]): PlaygroundAction[] =>
  actions.map((action, index) => ({
    ...action,
    id: action.id ?? `action-${index}`
  }));

export function buildManifestRecord(knobs?: Partial<ManifestStoryKnobs>): PlaygroundManifestRecord {
  const args: ManifestStoryKnobs = { ...defaultManifestKnobs, ...knobs };
  return {
    id: `${args.tenant}-${args.playground}-rev${args.revision}`,
    tenant: args.tenant,
    playground: args.playground,
    revision: args.revision,
    revisionLabel: args.revisionLabel || undefined,
    cookbook: args.cookbook || undefined,
    recipe: args.recipe || undefined,
    author: args.author || undefined,
    notes: args.notes || undefined,
    manifest: {
      metadata: { ...args.metadata },
      layout: { sections: cloneSections(args.sections) },
      actions: cloneActions(args.actions)
    },
    checksum: "e3c1c7f0f4ad96cf9a4df9fd6f8a93b1",
    createdAt: baseCreatedAt,
    updatedAt: Date.now()
  };
}
