import React, { useState } from "react";
import type { NotebookJobRecord } from "../../types";

interface Props {
  notebooks: NotebookJobRecord[];
  onRun: (parameters: Record<string, unknown>) => Promise<NotebookJobRecord>;
}

const formatTimestamp = (timestamp?: number) => {
  if (!timestamp) return "pending";
  return new Date(timestamp).toLocaleTimeString();
};

export const NotebookMonitor: React.FC<Props> = ({ notebooks, onRun }) => {
  const [dbPath, setDbPath] = useState("./interactions.db");
  const [statusUrl, setStatusUrl] = useState("http://localhost:8000/api/control/status");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleRun = async () => {
    setIsSubmitting(true);
    setFeedback(null);
    try {
      await onRun({ DB_PATH: dbPath, CONTROL_STATUS_URL: statusUrl, OUTPUT_DIR: "./_papermill" });
      setFeedback("Notebook run triggered");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setFeedback(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="control-card notebook-monitor">
      <header className="control-card__header">
        <div>
          <h2>Notebook monitor</h2>
          <p>Trigger Papermill runs and inspect the latest executions.</p>
        </div>
      </header>
      <div className="notebook-form">
        <label>
          DB Path
          <input value={dbPath} onChange={event => setDbPath(event.target.value)} />
        </label>
        <label>
          Control Status URL
          <input value={statusUrl} onChange={event => setStatusUrl(event.target.value)} />
        </label>
        <button onClick={handleRun} disabled={isSubmitting}>
          {isSubmitting ? "Triggering…" : "Run control_center_playground.ipynb"}
        </button>
        {feedback && <p className="notebook-feedback">{feedback}</p>}
      </div>
      <ul className="notebook-list">
        {notebooks.map(job => (
          <li key={job.id}>
            <div>
              <strong>{job.name}</strong>
              <span>{job.status.toUpperCase()}</span>
            </div>
            <p>
              Started: {formatTimestamp(job.startedAt)} · Completed: {formatTimestamp(job.completedAt)}
            </p>
          </li>
        ))}
        {!notebooks.length && <li>No notebook executions recorded yet.</li>}
      </ul>
    </section>
  );
};
