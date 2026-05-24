import type { Meta, StoryObj } from "@storybook/react";
import { IntegrityPanel } from "./IntegrityPanel";
import "../../styles.css";

const meta = {
  title: "Control Center/Integrity Panel",
  component: IntegrityPanel,
  parameters: {
    layout: "centered",
  },
} satisfies Meta<typeof IntegrityPanel>;

export default meta;

type Story = StoryObj<typeof IntegrityPanel>;

export const Healthy: Story = {
  args: {
    integrity: {
      summary: {
        total: 4821,
        modified: 0,
        missing: 0,
        drift: 0,
      },
    },
  },
};

export const DriftDetected: Story = {
  args: {
    integrity: {
      summary: {
        total: 4821,
        modified: 2,
        missing: 1,
        drift: 1,
      },
    },
  },
};

export const ErrorState: Story = {
  args: {
    integrity: {
      error: "project_integrity.py exited with status 1",
    },
  },
};

export const Empty: Story = {
  args: {
    integrity: null,
  },
};
