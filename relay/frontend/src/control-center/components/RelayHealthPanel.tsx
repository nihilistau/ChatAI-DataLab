/* --------------------------------------------------------------------------
 * Component: RelayHealthPanel
 * @tag:ui,ops,relay
 * ------------------------------------------------------------------------ */
import React from "react";
import { IntegrityPanel } from "./IntegrityPanel";
import { BugHuntPanel } from "./BugHuntPanel";

interface RelayStatus {
  relay: string;
  version: string;
  last_run?: string;
  user?: string;
  snapshot_exists: boolean;
  snapshot_created?: string;
  notebooks: string[];
  notebook_health: Record<string, boolean>;
  missing_dependencies: string[];
  api_health?: boolean;
  artifact_folder: string;
  artifact_retained: boolean;
  status_checked: string;
  integrity?: any;
  bughunt?: any;
}

export const RelayHealthPanel: React.FC<{ status: RelayStatus | null; error?: string; loading?: boolean }> = ({ status, error, loading }) => {
  if (loading) return <div className="control-card">Loading relay health…</div>;
  if (error) return <div className="control-card control-card--error">{error}</div>;
  if (!status) return <div className="control-card">No relay status available.</div>;

  return (
    <>
      <section className="control-card">
        <header className="control-card__header">
          <h2>Relay Health</h2>
          <span>Checked: {new Date(status.status_checked).toLocaleString()}</span>
        </header>
        <dl>
          <dt>Relay</dt>
          <dd>{status.relay}</dd>
          <dt>Version</dt>
          <dd>{status.version}</dd>
          <dt>User</dt>
          <dd>{status.user ?? "—"}</dd>
          <dt>Last Run</dt>
          <dd>{status.last_run ?? "—"}</dd>
          <dt>Snapshot</dt>
          <dd>{status.snapshot_exists ? `Created: ${status.snapshot_created}` : "Missing"}</dd>
          <dt>Artifact Retained</dt>
          <dd>{status.artifact_retained ? "Yes" : "No"}</dd>
          <dt>API Health</dt>
          <dd>{status.api_health === undefined ? "n/a" : status.api_health ? "Healthy" : "Unreachable"}</dd>
          <dt>Missing Dependencies</dt>
          <dd>{status.missing_dependencies.length === 0 ? "None" : status.missing_dependencies.join(", ")}</dd>
          <dt>Notebook Health</dt>
          <dd>
            <ul>
              {Object.entries(status.notebook_health).map(([nb, ok]) => (
                <li key={nb}>{nb}: {ok ? "OK" : "Error"}</li>
              ))}
            </ul>
          </dd>
        </dl>
      </section>
      <IntegrityPanel integrity={status.integrity ?? null} />
      <BugHuntPanel bughunt={status.bughunt ?? null} />
    </>
  );
};
