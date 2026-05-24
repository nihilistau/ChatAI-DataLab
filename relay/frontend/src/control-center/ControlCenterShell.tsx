import React from "react";
import { useControlCenter } from "./context";
import { MetricsPanel } from "./components/MetricsPanel";
import { ServiceGrid } from "./components/ServiceGrid";
import { NotebookMonitor } from "./components/NotebookMonitor";
import { CommandConsole } from "./components/CommandConsole";
import { TailLogViewer } from "./components/TailLogViewer";
import { ElementsPanel } from "./components/ElementsPanel";
import { RelayHealthPanel } from "./components/RelayHealthPanel";
import "./styles.css";

const formatUpdated = (timestamp: number | null) => (timestamp ? new Date(timestamp).toLocaleTimeString() : "—");

export const ControlCenterShell: React.FC = () => {
  const [relayStatus, setRelayStatus] = React.useState(null);
  const [relayError, setRelayError] = React.useState(null);
  const [relayLoading, setRelayLoading] = React.useState(true);
  const { status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook } = useControlCenter();

  React.useEffect(() => {
    setRelayLoading(true);
    fetch("/api/relay_status")
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch relay status");
        return res.json();
      })
      .then(data => {
        setRelayStatus(data);
        setRelayError(null);
      })
      .catch(e => setRelayError(e.message))
      .finally(() => setRelayLoading(false));
  }, []);

  const handleNotebookRun = (parameters: Record<string, unknown>) => triggerNotebook("control_center_relay.ipynb", parameters);

  return (
    <main className="control-center-shell">
      <header className="control-header">
        <div>
          <p>Control Center</p>
          <h1>Relay automation + Ops telemetry</h1>
        </div>
        <div className="header-actions">
          <span>Last updated: {formatUpdated(lastUpdated)}</span>
          <button onClick={() => refresh()} disabled={isRefreshing}>
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>
      {error && <div className="control-banner control-banner--error">{error}</div>}
      <RelayHealthPanel status={relayStatus} error={relayError ?? undefined} loading={relayLoading} />
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
