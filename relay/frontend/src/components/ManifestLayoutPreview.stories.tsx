import type { Meta, StoryObj } from "@storybook/react";
import ManifestLayoutPreview from "./ManifestLayoutPreview";
import type { ManifestStoryKnobs } from "../storybook/manifestStoryUtils";
import { buildManifestRecord, defaultManifestKnobs } from "../storybook/manifestStoryUtils";

const ManifestLayoutPreviewRelay = (props: ManifestStoryKnobs) => (
  <ManifestLayoutPreview manifest={buildManifestRecord(props)} />
);

const meta = {
  title: "Manifest/ManifestLayoutPreview",
  component: ManifestLayoutPreviewRelay,
  args: defaultManifestKnobs,
  argTypes: {
    metadata: { control: "object" },
    sections: { control: "object" },
    actions: { control: "object" },
    revision: { control: { type: "number", min: 1 } }
  }
} satisfies Meta<typeof ManifestLayoutPreviewRelay>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const HeroOnly: Story = {
  args: {
    sections: [],
    actions: [],
    metadata: {
      hero: "Workshop has not published widgets yet—use the Welcome Cookbook to push a layout.",
      notes: "Great for demonstrating the empty panel state."
    }
  }
};

export const ActionsOnly: Story = {
  args: {
    sections: [],
    actions: defaultManifestKnobs.actions
  }
};
