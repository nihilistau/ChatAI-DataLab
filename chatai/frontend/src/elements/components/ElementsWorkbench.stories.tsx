import type { Meta, StoryObj } from "@storybook/react";
import { ElementsWorkbench } from "./ElementsWorkbench";

const meta: Meta<typeof ElementsWorkbench> = {
  title: "Elements/Workbench",
  component: ElementsWorkbench,
  parameters: {
    layout: "fullscreen"
  }
};

export default meta;

type Story = StoryObj<typeof ElementsWorkbench>;

export const Default: Story = {
  render: () => <ElementsWorkbench />
};
