import type { Meta, StoryObj } from "@storybook/react";
import { RelayHealthPanel } from "./RelayHealthPanel";
import "../../styles.css";

const sampleStatus = {
  relay: "control-center",
  version: "v1.0.2",
  last_run: "2025-11-16T12:30:00Z",
  user: "ops-bot",
  snapshot_exists: true,
  snapshot_created: "2025-11-16T12:31:05Z",
  notebooks: ["workshop/notebooks/control_center_relay.ipynb"],
  notebook_health: {
    "workshop/notebooks/control_center_relay.ipynb": true,
    "workshop/notebooks/search_telemetry.ipynb": false,
  },
  missing_dependencies: [
    "azure-functions>=1.18",
  ],
  api_health: true,
  artifact_folder: "release_artifacts/v1.0.2-control",
  artifact_retained: true,
  status_checked: "2025-11-17T02:15:00Z",
  integrity: {
    summary: { total: 4120, modified: 0, missing: 0, drift: 0 },
  },
  bughunt: {
    findings: [
      { pattern: "console.log", matches: 2, files: ["src/control-center/ControlCenterShell.tsx"] },
      { pattern: "http://", matches: 0, files: [] },
    ],
  },
};

const meta = {
  title: "Control Center/Relay Health Panel",
  component: RelayHealthPanel,
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof RelayHealthPanel>;

export default meta;

type Story = StoryObj<typeof RelayHealthPanel>;

export const Healthy: Story = {
  args: {
    status: sampleStatus,
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    status: null,
    loading: true,
  },
};

export const Error: Story = {
  args: {
    status: null,
    error: "Failed to fetch relay status",
  },
};

export const MissingSnapshot: Story = {
  args: {
    status: {
      ...sampleStatus,
      snapshot_exists: false,
      snapshot_created: undefined,
      missing_dependencies: [],
      api_health: false,
    },
  },
};
