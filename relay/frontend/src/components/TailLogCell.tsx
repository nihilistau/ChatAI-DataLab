/**
 * Mirror of the backend tail log that keeps a copyable buffer in the UI.
 */
// @tag: frontend,component,telemetry

import { useMemo, useState } from "react";
import type { TailLogEntry } from "../types";

interface TailLogCellProps {
  entries: TailLogEntry[];
}

const formatEntry = (entry: TailLogEntry) => {
  const time = new Date(entry.createdAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
  return `${time} ${entry.source} · ${entry.message}`;
};

export default function TailLogCell({ entries }: TailLogCellProps) {
  const [copied, setCopied] = useState(false);

  const logBlob = useMemo(() => entries.map(formatEntry).join("\n"), [entries]);

  const handleCopy = async () => {
    if (!navigator?.clipboard) {
      return;
    }

    try {
      await navigator.clipboard.writeText(logBlob || "log idle");
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (error) {
      console.warn("Clipboard copy failed", error);
    }
  };

  return (
    <section className="tail-log-panel">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Tails feed</p>
          <h3>Selectable log output</h3>
        </div>
        <button type="button" className="ghost" onClick={handleCopy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </header>
      <div className="tail-log-scroll">
        {entries.length === 0 && <div className="empty-state">Tail log idle</div>}
        {entries.map((entry) => (
          <article key={entry.id} className="tail-log-entry">
            <header>
              <span>{new Date(entry.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
              <small>{entry.source}</small>
            </header>
            <p>{entry.message}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
