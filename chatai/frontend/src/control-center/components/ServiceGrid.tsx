import React from "react";
import type { OpsStatus } from "../../types";

interface Props {
  status: OpsStatus | null;
}

const formatUptime = (uptime?: number) => {
  if (!uptime) return "n/a";
  const minutes = Math.floor(uptime / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
};

export const ServiceGrid: React.FC<Props> = ({ status }) => {
  if (!status) {
    return <div className="control-card control-card--muted">Waiting for orchestrator snapshot…</div>;
  }

  return (
    <section className="control-card">
      <header className="control-card__header">
        <div>
          <h2>Service health</h2>
          <p>Aggregated view from Lab Orchestrator</p>
        </div>
      </header>
      <div className="service-grid">
        {status.services.map(service => (
          <article key={service.name} className="service-tile">
            <div className={`service-status ${service.state}`}>{service.state}</div>
            <h3>{service.display_name ?? service.name}</h3>
            <dl>
              <div>
                <dt>Runtime</dt>
                <dd>{service.runtime}</dd>
              </div>
              <div>
                <dt>Uptime</dt>
                <dd>{formatUptime(service.uptime)}</dd>
              </div>
              <div>
                <dt>PID</dt>
                <dd>{service.pid ?? "n/a"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
};
