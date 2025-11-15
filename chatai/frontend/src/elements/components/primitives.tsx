import React from "react";
import "../elements.css";

interface SurfaceProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
}

export const Surface: React.FC<SurfaceProps> = ({ title, description, children }) => (
  <section className="elements-surface">
    {title && (
      <header style={{ marginBottom: "0.75rem" }}>
        <p style={{ margin: 0, fontSize: "0.85rem", color: "#7dd3fc" }}>{title}</p>
        {description && (
          <span style={{ color: "#cbd5f5", fontSize: "0.85rem" }}>{description}</span>
        )}
      </header>
    )}
    {children}
  </section>
);

interface StackProps {
  gap?: string | number;
  direction?: "row" | "column";
  className?: string;
  children: React.ReactNode;
}

export const Stack: React.FC<StackProps> = ({ gap = "1rem", direction = "column", className, children }) => (
  <div className={`elements-stack ${className ?? ""}`.trim()} style={{ gap, flexDirection: direction }}>
    {children}
  </div>
);

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, hint }) => (
  <div style={{
    borderRadius: "12px",
    border: "1px solid rgba(148, 163, 184, 0.3)",
    padding: "0.75rem 1rem",
    background: "rgba(8, 47, 73, 0.5)",
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem"
  }}>
    <span style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#bae6fd" }}>{label}</span>
    <strong style={{ fontSize: "1.5rem", lineHeight: 1 }}>{value}</strong>
    {hint && <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>{hint}</span>}
  </div>
);
