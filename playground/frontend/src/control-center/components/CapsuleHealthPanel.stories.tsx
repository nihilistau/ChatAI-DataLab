import type { Meta, StoryObj } from "@storybook/react";
import { CapsuleHealthPanel } from "./CapsuleHealthPanel";
import "../../styles.css";

const sampleStatus = {
  capsule: "control-center",
  version: "v1.0.2",
  last_run: "2025-11-16T12:30:00Z",
  user: "ops-bot",
  snapshot_exists: true,
  snapshot_created: "2025-11-16T12:31:05Z",
  notebooks: ["datalab/notebooks/control_center_playground.ipynb"],
  notebook_health: {
    "datalab/notebooks/control_center_playground.ipynb": true,
    "datalab/notebooks/search_telemetry.ipynb": false,
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
  title: "Control Center/Capsule Health Panel",
  component: CapsuleHealthPanel,
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof CapsuleHealthPanel>;

export default meta;

type Story = StoryObj<typeof CapsuleHealthPanel>;

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
    error: "Failed to fetch capsule status",
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
