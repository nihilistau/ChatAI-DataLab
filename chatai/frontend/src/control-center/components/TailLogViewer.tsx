import React, { useEffect, useState } from "react";
import { fetchControlLogs } from "../../lib/api";

const SERVICES = ["backend", "frontend", "datalab", "playground"];

export const TailLogViewer: React.FC = () => {
  const [service, setService] = useState<string>(SERVICES[0]);
  const [lines, setLines] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await fetchControlLogs(service, 120);
        if (active) {
          setLines(response.lines);
          setError(null);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        if (active) {
          setError(message);
        }
      }
    };

    void load();
    const id = window.setInterval(() => {
      void load();
    }, 4000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, [service]);

  return (
    <section className="control-card tail-log-viewer">
      <header className="control-card__header">
        <div>
          <h2>Tail logs</h2>
          <p>
            Streaming from <code>{`.labctl/logs/${service}.log`}</code>.
          </p>
        </div>
        <select value={service} onChange={event => setService(event.target.value)}>
          {SERVICES.map(name => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </header>
      {error && <p className="error-text">{error}</p>}
      <pre className="log-output" aria-live="polite">
        {lines.length ? lines.join("\n") : "No log lines yet."}
      </pre>
    </section>
  );
};
