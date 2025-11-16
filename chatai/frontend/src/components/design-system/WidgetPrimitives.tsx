import type { ReactNode } from "react";
import { ACCENT_MAP, type AccentColor, type LightingPreset, type WidgetTone, TONE_EMPHASIS } from "./DesignTokens";
import "./design-system.css";

export type WidgetSurfaceProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  accent?: AccentColor;
  tone?: WidgetTone;
  actions?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  dense?: boolean;
};

const accentStyle = (accent: AccentColor | undefined): LightingPreset => {
  if (!accent) {
    return ACCENT_MAP.violet;
  }
  return ACCENT_MAP[accent];
};

export function WidgetSurface({
  title,
  eyebrow,
  description,
  accent = "violet",
  tone = "neutral",
  actions,
  footer,
  children,
  dense
}: WidgetSurfaceProps) {
  const palette = accentStyle(accent);
  const emphasis = TONE_EMPHASIS[tone];
  return (
    <article
      className="ds-widget"
      style={{ borderColor: palette.stroke, boxShadow: palette.glow, padding: dense ? "1rem" : undefined }}
    >
      {eyebrow && <p className="ds-eyebrow">{eyebrow}</p>}
      <header className="panel-header" style={{ alignItems: "flex-start" }}>
        <div>
          <h3>{title}</h3>
          {description && <p>{description}</p>}
        </div>
        {actions}
      </header>
      <div>{children}</div>
      {footer && <footer style={{ marginTop: "0.75rem", color: emphasis.color }}>{footer}</footer>}
    </article>
  );
}

export function MetricValue({ label, value, delta }: { label: string; value: string; delta?: string }) {
  return (
    <div>
      <div className="ds-metric-value">{value}</div>
      <div className="ds-metric-caption">{label}</div>
      {delta && <small className="ds-highlight">{delta}</small>}
    </div>
  );
}

export function Sparkline({ points, stroke = "#7de2e0" }: { points: number[]; stroke?: string }) {
  const normalized = points.map((point) => Math.max(1, Math.min(100, point)));
  const path = normalized
    .map((point, index) => {
      const x = (index / Math.max(1, normalized.length - 1)) * 100;
      const y = 100 - point;
      return `${index === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  return (
    <svg className="ds-sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`spark-${stroke}`} x1="0%" x2="0%" y1="0%" y2="100%">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.65" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={path} fill="none" stroke={stroke} strokeWidth={2.2} strokeLinecap="round" />
      <path d={`${path} L100,100 L0,100 Z`} fill={`url(#spark-${stroke})`} opacity={0.35} />
    </svg>
  );
}

export function RadialGauge({
  value,
  accent = "lime",
  label
}: {
  value: number;
  accent?: AccentColor;
  label: string;
}) {
  const clamped = Math.min(100, Math.max(0, value));
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const palette = accentStyle(accent);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.25rem" }}>
      <svg className="ds-gauge" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} stroke="rgba(255,255,255,0.08)" strokeWidth={8} fill="none" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          stroke={palette.stroke}
          strokeWidth={8}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="none"
        />
        <text x="60" y="66" textAnchor="middle" fontSize="1.4rem" fill="#e2e8f0">
          {clamped}%
        </text>
      </svg>
      <span className="ds-metric-caption">{label}</span>
    </div>
  );
}

export function StatusList({ items }: { items: Array<{ label: string; status: string; tone?: WidgetTone }> }) {
  return (
    <div className="ds-bento">
      {items.map((item) => (
        <div key={item.label}>
          <small className="ds-metric-caption">{item.label}</small>
          <div className="ds-highlight" style={{ color: TONE_EMPHASIS[item.tone ?? "info"].color }}>
            {item.status}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ActionDock({ actions }: { actions: Array<{ label: string; intent?: WidgetTone }> }) {
  return (
    <div className="ds-toolbar">
      {actions.map((action) => (
        <button key={action.label} type="button" style={TONE_EMPHASIS[action.intent ?? "neutral"]}>
          {action.label}
        </button>
      ))}
    </div>
  );
}
