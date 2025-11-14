import type { Meta, StoryObj } from "@storybook/react";
import React from "react";
import { ControlCenterShell } from "./ControlCenterShell";
import { ControlCenterContext } from "./context";
import type { ControlWidgetSnapshot, NotebookJobRecord, OpsStatus } from "../types";

const sampleStatus: OpsStatus = {
  services: [
    { name: "backend", state: "running", runtime: "windows", pid: 1111, uptime: 600, display_name: "FastAPI" },
    { name: "frontend", state: "running", runtime: "linux", pid: 2222, uptime: 480, display_name: "Ops Deck" }
  ],
  processes: [],
  network: { hostname: "storybook", platform: "windows", uptime: 3600, bytes_sent: 0, bytes_recv: 0, interfaces: {} },
  logs: {},
  timestamp: Date.now()
};

const sampleWidgets: ControlWidgetSnapshot = {
  generatedAt: Date.now(),
  metrics: [
    { id: "latency", label: "LLM Latency", value: 820, changePct: -4.2, unit: "ms" },
    { id: "ru-burn", label: "RU Burn", value: 50, changePct: 1.1, unit: "RU/s" },
    { id: "keystrokes", label: "Keystrokes", value: 4200, changePct: 2.0, unit: "events/min" }
  ],
  sparklines: {
    latency: [900, 870, 880, 820],
    ru: [40, 42, 44, 50],
    throughput: [3000, 3400, 3600, 4200]
  },
  ruBudget: { total: 120000, consumed: 40000, remaining: 80000 }
};

const sampleNotebooks: NotebookJobRecord[] = [
  {
    id: "storybook-job",
    name: "control_center_playground.ipynb",
    status: "succeeded",
    createdAt: Date.now() - 60000,
    startedAt: Date.now() - 55000,
    completedAt: Date.now() - 50000,
    parameters: {}
  }
];

const meta = {
  title: "Control Center/ControlCenterShell",
  component: ControlCenterShell,
  decorators: [
    (Story) => (
      <ControlCenterContext.Provider
        value={{
          status: sampleStatus,
          widgets: sampleWidgets,
          notebooks: sampleNotebooks,
          lastUpdated: Date.now(),
          isRefreshing: false,
          error: null,
          refresh: async () => undefined,
          triggerNotebook: async () => sampleNotebooks[0]
        }}
      >
        <Story />
      </ControlCenterContext.Provider>
    )
  ]
} satisfies Meta<typeof ControlCenterShell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
