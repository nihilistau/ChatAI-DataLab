import React from "react";
import { useControlCenter } from "./context";
import { MetricsPanel } from "./components/MetricsPanel";
import { ServiceGrid } from "./components/ServiceGrid";
import { NotebookMonitor } from "./components/NotebookMonitor";
import { CommandConsole } from "./components/CommandConsole";
import { TailLogViewer } from "./components/TailLogViewer";
import "./styles.css";

const formatUpdated = (timestamp: number | null) => (timestamp ? new Date(timestamp).toLocaleTimeString() : "—");

export const ControlCenterShell: React.FC = () => {
  const { status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook } = useControlCenter();

  const handleNotebookRun = (parameters: Record<string, unknown>) => triggerNotebook("control_center_playground.ipynb", parameters);

  return (
    <main className="control-center-shell">
      <header className="control-header">
        <div>
          <p>Control Center</p>
          <h1>Playground automation + Ops telemetry</h1>
        </div>
        <div className="header-actions">
          <span>Last updated: {formatUpdated(lastUpdated)}</span>
          <button onClick={() => refresh()} disabled={isRefreshing}>
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>
      {error && <div className="control-banner control-banner--error">{error}</div>}
      <MetricsPanel widgets={widgets} />
      <div className="control-grid control-grid--two-column">
        <ServiceGrid status={status} />
        <NotebookMonitor notebooks={notebooks} onRun={handleNotebookRun} />
      </div>
      <div className="control-grid control-grid--two-column">
        <CommandConsole />
        <TailLogViewer />
      </div>
    </main>
  );
};
