/**
 * Control panel for orchestrating backend/frontend/kitchen services plus
 * viewing logs, processes, and network stats.
 */
// @tag: frontend,component,ops

import { useMemo, useState } from "react";
import type { OpsAction, OpsStatus, ServiceStatus } from "../types";

type Props = {
  status: OpsStatus | null;
  onCommand: (action: OpsAction, target?: string) => Promise<void>;
  busyAction?: OpsAction | null;
};

const SERVICE_ORDER = ["backend", "frontend", "kitchen"] as const;
const WORKFLOWS: Array<{ title: string; steps: string[]; actions: OpsAction[]; target?: string }> = [
  {
    title: "Full stack reboot",
    steps: ["Stop all services", "Flush caches", "Restart orchestration"],
    actions: ["stop", "kill-all", "start"] as OpsAction[]
  },
  {
    title: "Frontend refresh",
    steps: ["Restart Vite dev server", "Open telemetry stream"],
    actions: ["restart", "logs"] as OpsAction[],
    target: "frontend"
  },
  {
    title: "Kitchen warm-up",
    steps: ["Start notebooks", "Tail lab logs"],
    actions: ["start", "logs"] as OpsAction[],
    target: "kitchen"
  }
];

function formatSeconds(seconds?: number): string {
  if (!seconds || seconds < 0) return "—";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
}

const OpsDeck = ({ status, onCommand, busyAction = null }: Props) => {
  const [selectedService, setSelectedService] = useState<string>(SERVICE_ORDER[0]);

  const serviceSnapshot = useMemo<ServiceStatus | undefined>(() => {
    if (!status) return undefined;
    const direct = status.services.find((svc) => svc.name === selectedService);
    if (direct) return direct;
    return status.services[0];
  }, [status, selectedService]);

  const logLines = serviceSnapshot ? status?.logs?.[serviceSnapshot.name] ?? [] : [];
  const processes = status?.processes ?? [];
  const network = status?.network;

  const handleAction = async (action: OpsAction, target?: string) => {
    await onCommand(action, target ?? serviceSnapshot?.name);
  };

  return (
    <section className="ops-deck">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Control center</h2>
        </div>
        <div className="ops-service-selector">
          {SERVICE_ORDER.map((service) => (
            <button
              key={service}
              className={service === (serviceSnapshot?.name ?? selectedService) ? "chip active" : "chip"}
              onClick={() => setSelectedService(service)}
            >
              {service}
            </button>
          ))}
        </div>
      </header>

      <div className="ops-grid">
        <div className="ops-glass">
          <div className="ops-service-meta">
            <div>
              <p className="eyebrow">Service</p>
              <h3>{serviceSnapshot?.display_name ?? serviceSnapshot?.name ?? "—"}</h3>
            </div>
            <div className={`status-pill ${serviceSnapshot?.state?.toLowerCase() ?? "idle"}`}>
              {serviceSnapshot?.state ?? "idle"}
            </div>
          </div>
          <div className="ops-actions">
            <button onClick={() => handleAction("start")} disabled={busyAction === "start"}>
              Start
            </button>
            <button onClick={() => handleAction("restart")} disabled={busyAction === "restart"}>
              Restart
            </button>
            <button onClick={() => handleAction("stop")} disabled={busyAction === "stop"}>
              Stop
            </button>
            <button className="danger" onClick={() => handleAction("kill")} disabled={busyAction === "kill"}>
              Kill
            </button>
          </div>
          <dl className="ops-meta">
            <div>
              <dt>Runtime</dt>
              <dd>{serviceSnapshot?.runtime ?? "—"}</dd>
            </div>
            <div>
              <dt>PID</dt>
              <dd>{serviceSnapshot?.pid ?? "—"}</dd>
            </div>
            <div>
              <dt>Uptime</dt>
              <dd>{formatSeconds(serviceSnapshot?.uptime)}</dd>
            </div>
          </dl>
        </div>

        <div className="ops-terminal">
          <header>
            <span>log · {serviceSnapshot?.name ?? "—"}</span>
            <div className="terminal-actions">
              <button onClick={() => handleAction("logs")} disabled={busyAction === "logs"}>
                Refresh
              </button>
            </div>
          </header>
          <pre>
            {(logLines.length ? logLines : ["No log entries yet."]).map((line) => (
              <span key={line + Math.random()}>{line}
</span>
            ))}
          </pre>
        </div>
      </div>

      <div className="ops-lower">
        <div className="process-panel">
          <div className="panel-subheader">
            <p className="eyebrow">Processes</p>
            <button onClick={() => handleAction("status")} disabled={busyAction === "status"}>
              Snapshot
            </button>
          </div>
          <div className="process-table">
            <div className="process-row head">
              <span>PID</span>
              <span>Name</span>
              <span>CPU</span>
              <span>Memory</span>
              <span>Uptime</span>
            </div>
            {processes.map((proc) => (
              <div className="process-row" key={proc.pid}>
                <span>{proc.pid}</span>
                <span>{proc.name ?? "—"}</span>
                <span>{proc.cpu.toFixed(1)}%</span>
                <span>{proc.memory.toFixed(1)}%</span>
                <span>{formatSeconds(proc.uptime)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="network-panel">
          <p className="eyebrow">Network</p>
          <h3>{network?.hostname ?? "—"}</h3>
          <ul>
            <li>Platform · {network?.platform ?? "unknown"}</li>
            <li>Uptime · {formatSeconds(network?.uptime)}</li>
            <li>Sent · {network ? (network.bytes_sent / 1_000_000).toFixed(1) : "0"} MB</li>
            <li>Recv · {network ? (network.bytes_recv / 1_000_000).toFixed(1) : "0"} MB</li>
          </ul>
        </div>

        <div className="workflow-panel">
          <p className="eyebrow">Workflows</p>
          <div className="workflow-grid">
            {WORKFLOWS.map((flow) => (
              <article key={flow.title}>
                <header>
                  <h4>{flow.title}</h4>
                  <small>{flow.steps.length} steps</small>
                </header>
                <ol>
                  {flow.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <div className="workflow-actions">
                  {flow.actions.map((action) => (
                    <button
                      key={`${flow.title}-${action}`}
                      onClick={() => handleAction(action, flow.target)}
                      disabled={busyAction === action}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default OpsDeck;
