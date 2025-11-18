import type { Decorator, Meta, StoryObj } from "@storybook/react";
import React from "react";
import ManifestWidgetSummary from "./ManifestWidgetSummary";
import { ManifestContext, type ManifestContextValue } from "../context/ManifestContext";
import type { ManifestStoryKnobs } from "../storybook/manifestStoryUtils";
import { buildManifestRecord, defaultManifestKnobs } from "../storybook/manifestStoryUtils";

interface ManifestSummaryStoryArgs extends ManifestStoryKnobs {
  hasManifest: boolean;
  loading: boolean;
  error: string | null;
  status: string | null;
}

const ManifestStoryDecorator: Decorator = (Story, context) => {
  const args = context.args as unknown as ManifestSummaryStoryArgs;
  const manifestRecord = args.hasManifest ? buildManifestRecord(args) : null;

  const value: ManifestContextValue = {
    tenant: args.tenant,
    playground: args.playground,
    manifest: manifestRecord,
    loading: args.loading,
    refreshing: false,
    error: args.error,
    status: args.status,
    lastFetched: manifestRecord ? manifestRecord.updatedAt : null,
    refresh: async () => undefined,
    pollIntervalMs: 60000,
    autoRefreshEnabled: false,
    setAutoRefreshEnabled: () => undefined
  };

  return (
    <ManifestContext.Provider value={value}>
      <div style={{ maxWidth: 520 }}>
        <Story />
      </div>
    </ManifestContext.Provider>
  );
};

const meta = {
  title: "Manifest/ManifestWidgetSummary",
  component: ManifestWidgetSummary,
  decorators: [ManifestStoryDecorator],
  args: {
    ...defaultManifestKnobs,
    hasManifest: true,
    loading: false,
    error: null,
    status: null
  },
  argTypes: {
    metadata: { control: "object" },
    sections: { control: "object" },
    actions: { control: "object" }
  }
} satisfies Meta<typeof ManifestWidgetSummary>;

export default meta;
type Story = StoryObj<ManifestSummaryStoryArgs>;

export const Default: Story = {};

export const Loading: Story = {
  args: {
    hasManifest: false,
    loading: true
  }
};

export const ErrorState: Story = {
  args: {
    hasManifest: false,
    loading: false,
    error: "Failed to reach manifest API"
  }
};

export const EmptyManifest: Story = {
  args: {
    sections: [],
    actions: [],
    metadata: {},
    notes: "",
    hasManifest: true
  }
};

export const PendingPublish: Story = {
  args: {
    hasManifest: false,
    loading: false,
    status: "Publish from Kitchen to hydrate this manifest"
  }
};
