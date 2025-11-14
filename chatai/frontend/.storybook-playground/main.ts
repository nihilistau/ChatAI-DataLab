import type { StorybookConfig } from "@storybook/react-vite";
import baseConfig from "../.storybook/main";

const config: StorybookConfig = {
  ...baseConfig,
  stories: ["../src/control-center/**/*.stories.@(ts|tsx)"],
};

export default config;
