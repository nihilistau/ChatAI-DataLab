import React from "react";
import type { ControlWidgetSnapshot } from "../../types";

interface Props {
  widgets: ControlWidgetSnapshot | null;
}

const formatValue = (value: number, unit?: string) => {
  const rounded = Math.round(value * 100) / 100;
  return unit ? `${rounded.toLocaleString()} ${unit}` : rounded.toLocaleString();
};

const Sparkline: React.FC<{ points: number[] }> = ({ points }) => {
  if (!points.length) return null;
  const maxValue = Math.max(...points);
  return (
    <div className="control-sparkline" aria-label="trend sparkline">
      {points.map((point, idx) => {
        const height = maxValue === 0 ? 0 : (point / maxValue) * 100;
        return <span key={`spark-${idx}`} style={{ height: `${height || 2}%` }} />;
      })}
    </div>
  );
};

export const MetricsPanel: React.FC<Props> = ({ widgets }) => {
  if (!widgets) {
    return <div className="control-card control-card--muted">Loading metrics…</div>;
  }

  return (
    <section className="control-metrics" aria-live="polite">
      {widgets.metrics.map(metric => (
        <article key={metric.id} className="control-card">
          <header>
            <span className="metric-label">{metric.label}</span>
            <span className={`metric-change ${metric.changePct >= 0 ? "positive" : "negative"}`}>
              {metric.changePct >= 0 ? "▲" : "▼"} {Math.abs(metric.changePct).toFixed(2)}%
            </span>
          </header>
          <div className="metric-value">{formatValue(metric.value, metric.unit)}</div>
          <Sparkline points={widgets.sparklines[metric.id === "ru-burn" ? "ru" : metric.id === "keystrokes" ? "throughput" : "latency"] ?? []} />
        </article>
      ))}
      <article className="control-card">
        <header>
          <span className="metric-label">RU Budget</span>
        </header>
        <div className="ru-budget">
          <div className="ru-budget__bar">
            <div
              className="ru-budget__bar-fill"
              style={{ width: `${(widgets.ruBudget.consumed / widgets.ruBudget.total) * 100}%` }}
            />
          </div>
          <p>{widgets.ruBudget.remaining.toLocaleString()} RU remaining</p>
        </div>
      </article>
    </section>
  );
};
