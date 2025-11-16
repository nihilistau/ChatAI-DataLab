import type { CSSProperties } from "react";

export type AccentColor = "lime" | "forest" | "peach" | "violet" | "plasma" | "cobalt" | "ember";

export type WidgetTone = "neutral" | "success" | "warning" | "danger" | "info";

export type LightingPreset = {
  stroke: string;
  glow: string;
  accent: string;
};

export const ACCENT_MAP: Record<AccentColor, LightingPreset> = {
  lime: {
    stroke: "rgba(181, 243, 106, 0.45)",
    glow: "0 15px 45px rgba(181, 243, 106, 0.22)",
    accent: "linear-gradient(135deg, #b5f36a, #4aa871)"
  },
  forest: {
    stroke: "rgba(15, 164, 127, 0.5)",
    glow: "0 18px 50px rgba(61, 218, 215, 0.18)",
    accent: "linear-gradient(135deg, #3ddad7, #0b7561)"
  },
  peach: {
    stroke: "rgba(255, 170, 142, 0.45)",
    glow: "0 20px 45px rgba(255, 170, 142, 0.25)",
    accent: "linear-gradient(135deg, #ffb7a3, #f25f8b)"
  },
  violet: {
    stroke: "rgba(157, 123, 255, 0.5)",
    glow: "0 24px 60px rgba(142, 105, 255, 0.3)",
    accent: "linear-gradient(135deg, #7e7bff, #b77bff)"
  },
  plasma: {
    stroke: "rgba(93, 244, 255, 0.45)",
    glow: "0 30px 60px rgba(93, 244, 255, 0.35)",
    accent: "linear-gradient(135deg, #15b8a6, #5df4ff)"
  },
  cobalt: {
    stroke: "rgba(89, 148, 255, 0.55)",
    glow: "0 28px 68px rgba(89, 148, 255, 0.32)",
    accent: "linear-gradient(135deg, #2f6bff, #00bcd4)"
  },
  ember: {
    stroke: "rgba(255, 156, 99, 0.55)",
    glow: "0 25px 60px rgba(255, 156, 99, 0.35)",
    accent: "linear-gradient(135deg, #ff8c42, #ffdd7a)"
  }
};

export const TONE_EMPHASIS: Record<WidgetTone, CSSProperties> = {
  neutral: {
    color: "#e2e8f0",
    borderColor: "rgba(148, 163, 184, 0.35)",
    background: "rgba(8, 12, 24, 0.7)"
  },
  success: {
    color: "#b5f36a",
    borderColor: "rgba(181, 243, 106, 0.45)",
    background: "rgba(41, 81, 32, 0.65)"
  },
  warning: {
    color: "#ffd07a",
    borderColor: "rgba(255, 208, 122, 0.45)",
    background: "rgba(82, 63, 25, 0.65)"
  },
  danger: {
    color: "#ff7a8a",
    borderColor: "rgba(255, 122, 138, 0.5)",
    background: "rgba(122, 20, 47, 0.55)"
  },
  info: {
    color: "#7de2e0",
    borderColor: "rgba(125, 226, 224, 0.45)",
    background: "rgba(19, 68, 82, 0.7)"
  }
};

export const GRID_GAP = 24;
export const PANEL_RADIUS = 20;
export const PANEL_BORDER = "1px solid rgba(255, 255, 255, 0.08)";

export const WIDGET_GRADIENTS = [
  "linear-gradient(135deg, rgba(4, 18, 31, 0.9), rgba(3, 5, 14, 0.85))",
  "linear-gradient(145deg, rgba(15, 20, 34, 0.95), rgba(6, 12, 24, 0.85))",
  "linear-gradient(125deg, rgba(8, 10, 18, 0.95), rgba(10, 20, 28, 0.8))",
  "linear-gradient(155deg, rgba(16, 7, 22, 0.9), rgba(8, 20, 32, 0.85))"
];

export const SECTION_TITLES = {
  telemetry: "Telemetry widgets",
  control: "Control widgets",
  narrative: "Narrative widgets"
} as const;
