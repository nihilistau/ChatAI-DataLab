import React, { useState } from "react";
import type { OpsAction } from "../../types";
import { sendOpsCommand } from "../../lib/api";

const ACTIONS: OpsAction[] = ["status", "start", "stop", "restart", "logs"];

export const CommandConsole: React.FC = () => {
  const [action, setAction] = useState<OpsAction>("status");
  const [target, setTarget] = useState("backend");
  const [output, setOutput] = useState<string>("Ready.");
  const [isRunning, setIsRunning] = useState(false);

  const handleRun = async () => {
    setIsRunning(true);
    try {
      const response = await sendOpsCommand({ action, target });
      setOutput(response.output || JSON.stringify(response, null, 2));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setOutput(message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <section className="control-card command-console">
      <header className="control-card__header">
        <div>
          <h2>Command console</h2>
          <p>Send Ops Deck commands via the FastAPI relay.</p>
        </div>
      </header>
      <div className="command-console__form">
        <label>
          Action
          <select value={action} onChange={event => setAction(event.target.value as OpsAction)}>
            {ACTIONS.map(option => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          Target
          <select value={target} onChange={event => setTarget(event.target.value)}>
            {['backend', 'frontend', 'datalab', 'all'].map(name => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button onClick={handleRun} disabled={isRunning}>
          {isRunning ? "Running…" : "Execute"}
        </button>
      </div>
      <pre className="command-console__output" aria-live="polite">
        {output}
      </pre>
    </section>
  );
};
