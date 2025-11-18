import type { Meta, StoryObj } from "@storybook/react";
import { BugHuntPanel } from "./BugHuntPanel";
import "../../styles.css";

const meta = {
  title: "Control Center/Bug Hunt Panel",
  component: BugHuntPanel,
  parameters: {
    layout: "centered",
  },
} satisfies Meta<typeof BugHuntPanel>;

export default meta;

type Story = StoryObj<typeof BugHuntPanel>;

export const Findings: Story = {
  args: {
    bughunt: {
      findings: [
        { pattern: "console.log", matches: 4, files: ["src/App.tsx", "src/control-center/ControlCenterShell.tsx"] },
        { pattern: "http://", matches: 1, files: ["src/lib/http.ts"] },
      ],
    },
  },
};

export const CleanSweep: Story = {
  args: {
    bughunt: {
      findings: [],
    },
  },
};

export const ErrorState: Story = {
  args: {
    bughunt: {
      error: "LabControl SearchToolkit failed to run",
    },
  },
};

export const Empty: Story = {
  args: {
    bughunt: null,
  },
};
