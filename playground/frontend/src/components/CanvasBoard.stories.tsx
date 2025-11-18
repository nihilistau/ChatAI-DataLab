import type { Meta, StoryObj } from "@storybook/react";
import CanvasBoard from "./CanvasBoard";
import type { CanvasItem } from "../types";

const sampleItems: CanvasItem[] = [
  {
    id: "hypothesis-1",
    owner: "user",
    title: "Agents can triage anomaly feeds",
    body: "Test if the L4 triage agent can classify 200 alerts/hour with <2% error.",
    accent: "forest",
    updatedAt: Date.now() - 1000 * 60 * 15,
    category: "hypothesis",
  },
  {
    id: "shared-1",
    owner: "shared",
    title: "Latency regression on westus-backend",
    body: "p95 latency climbed to 1.4s after build #4432.",
    accent: "lime",
    updatedAt: Date.now() - 1000 * 60 * 5,
    category: "signal",
  },
  {
    id: "assistant-1",
    owner: "assistant",
    title: "Notebook memory leak",
    body: "Top cgroup crosses 7GB when Papermill loops 5× in dev.",
    accent: "violet",
    updatedAt: Date.now() - 1000 * 60 * 2,
    category: "insight",
  },
];

const meta: Meta<typeof CanvasBoard> = {
  title: "Components/CanvasBoard",
  component: CanvasBoard,
  args: {
    items: sampleItems,
    onMove: () => undefined,
    onCreate: () => undefined,
    onPromoteToArtifact: () => undefined,
  },
};

export default meta;

type Story = StoryObj<typeof CanvasBoard>;

export const Default: Story = {};

export const EmptyBoard: Story = {
  args: {
    items: [],
  },
};
