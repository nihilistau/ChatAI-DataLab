import React from "react";
import { useControlCenter } from "./context";
import { MetricsPanel } from "./components/MetricsPanel";
import { ServiceGrid } from "./components/ServiceGrid";
import { NotebookMonitor } from "./components/NotebookMonitor";
import { CommandConsole } from "./components/CommandConsole";
import { TailLogViewer } from "./components/TailLogViewer";
import { ElementsPanel } from "./components/ElementsPanel";
import { CapsuleHealthPanel } from "./components/CapsuleHealthPanel";
import "./styles.css";

const formatUpdated = (timestamp: number | null) => (timestamp ? new Date(timestamp).toLocaleTimeString() : "—");

export const ControlCenterShell: React.FC = () => {
  const [capsuleStatus, setCapsuleStatus] = React.useState(null);
  const [capsuleError, setCapsuleError] = React.useState(null);
  const [capsuleLoading, setCapsuleLoading] = React.useState(true);
  const { status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook } = useControlCenter();

  React.useEffect(() => {
    setCapsuleLoading(true);
    fetch("/api/capsule_status")
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch capsule status");
        return res.json();
      })
      .then(data => {
        setCapsuleStatus(data);
        setCapsuleError(null);
      })
      .catch(e => setCapsuleError(e.message))
      .finally(() => setCapsuleLoading(false));
  }, []);

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
      <CapsuleHealthPanel status={capsuleStatus} error={capsuleError ?? undefined} loading={capsuleLoading} />
      <MetricsPanel widgets={widgets} />
      <div className="control-grid control-grid--two-column">
        <ServiceGrid status={status} />
        <NotebookMonitor notebooks={notebooks} onRun={handleNotebookRun} />
      </div>
      <div className="control-grid control-grid--two-column">
        <CommandConsole />
        <TailLogViewer />
      </div>
      <ElementsPanel />
    </main>
  );
};
