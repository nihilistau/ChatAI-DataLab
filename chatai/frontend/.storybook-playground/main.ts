import type { StorybookConfig } from "@storybook/react-vite";
// eslint-disable-next-line import/extensions
// @ts-ignore - Storybook bundler resolves .ts config imports
import baseConfig from "../.storybook/main.ts";

const config: StorybookConfig = {
  ...baseConfig,
  stories: ["../src/control-center/**/*.stories.@(ts|tsx)"],
};

export default config;
