import { useCallback, useState } from "react";

import type { ReleaseLogEntry } from "../types";

interface ReleaseLogPanelProps {
  entries: ReleaseLogEntry[];
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

const KIND_LABELS: Record<string, string> = {
  release_pipeline: "Release pipeline",
  workflow_harness: "Workflow harness"
};

const STATUS_LABELS: Record<string, string> = {
  ok: "Success",
  failed: "Failed",
  skipped: "Skipped",
  running: "Running"
};

const TIMESTAMP_FORMAT: Intl.DateTimeFormatOptions = {
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit"
};

const formatDuration = (value?: number): string | null => {
  if (value === undefined || value === null || Number.isNaN(value)) return null;
  if (value < 60) return `${value.toFixed(1)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
};

const formatStatusLabel = (status?: string | null): string => {
  if (!status) return "Success";
  return STATUS_LABELS[status] ?? status;
};

const safeDetails = (details: unknown): string => {
  if (typeof details === "string") return details;
  if (typeof details === "number" || typeof details === "boolean") return String(details);
  if (details && typeof details === "object") {
    try {
      return JSON.stringify(details);
    } catch {
      return "details";
    }
  }
  return "";
};

export default function ReleaseLogPanel({ entries, loading, error, onRefresh }: ReleaseLogPanelProps) {
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  const handleCopy = useCallback((value: string) => {
    if (typeof navigator === "undefined" || !navigator.clipboard) return;
    navigator.clipboard.writeText(value).catch(() => {
      /* no-op */
    });
  }, []);

  const handleRefresh = () => {
    if (loading) return;
    onRefresh?.();
  };

  const toggleTimeline = (id: string) => {
    setExpandedEntry((prev) => (prev === id ? null : id));
  };

  return (
    <section className="release-log-panel">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Release log</p>
          <h3>Ops audit trail</h3>
        </div>
        {onRefresh && (
          <button type="button" className="ghost" onClick={handleRefresh} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        )}
      </header>
      {error && <p className="ops-error">{error}</p>}
      {!loading && entries.length === 0 && !error && <div className="empty-state">No release entries recorded yet.</div>}
      <div className="release-log-list">
        {entries.map((entry) => {
          const timeline = entry.timeline ?? [];
          const isExpanded = expandedEntry === entry.id;
          const visibleTimeline = isExpanded ? timeline : timeline.slice(0, 4);
          const commitShort = entry.commit ? entry.commit.slice(0, 8) : null;

          return (
            <article key={entry.id} className="release-log-entry">
              <header>
                <span>{new Date(entry.timestamp).toLocaleString(undefined, TIMESTAMP_FORMAT)}</span>
                <small>
                  {entry.source ? `${entry.source} · ` : ""}
                  {KIND_LABELS[entry.kind] ?? entry.kind}
                </small>
              </header>
              <div className="release-log-title">
                <strong>{entry.tag || entry.releaseTag || entry.kind}</strong>
                {entry.branch && <span>{entry.branch}</span>}
              </div>
              <div className="release-log-chips">
                {entry.action && <span className="release-chip accent">{entry.action}</span>}
                <span className={`status-chip ${entry.status ?? "ok"}`}>{formatStatusLabel(entry.status)}</span>
                {typeof entry.durationSeconds === "number" && (
                  <span className="release-chip subtle">{formatDuration(entry.durationSeconds)}</span>
                )}
                {entry.source && <span className="release-chip subtle">{entry.source}</span>}
              </div>
              {entry.notes && <p className="release-log-notes">{entry.notes}</p>}
              {entry.summary && <p className="release-log-summary">{entry.summary}</p>}
              {entry.error && <p className="release-log-error">{entry.error}</p>}
              <dl className="release-log-meta">
                {commitShort && (
                  <div>
                    <dt>Commit</dt>
                    <dd>{commitShort}</dd>
                  </div>
                )}
                {entry.releaseDir && (
                  <div>
                    <dt>Artifacts</dt>
                    <dd>
                      <span>{entry.releaseDir}</span>
                      <button type="button" className="copy-button" onClick={() => handleCopy(entry.releaseDir)}>
                        Copy
                      </button>
                    </dd>
                  </div>
                )}
                {entry.releaseMode && (
                  <div>
                    <dt>Mode</dt>
                    <dd>{entry.releaseMode}</dd>
                  </div>
                )}
                {entry.releaseTag && (
                  <div>
                    <dt>Release tag</dt>
                    <dd>{entry.releaseTag}</dd>
                  </div>
                )}
                {entry.checkpointTag && (
                  <div>
                    <dt>Checkpoint</dt>
                    <dd>{entry.checkpointTag}</dd>
                  </div>
                )}
                {entry.reference && (
                  <div>
                    <dt>Reference</dt>
                    <dd>{entry.reference}</dd>
                  </div>
                )}
              </dl>
              {entry.details && <div className="release-log-details">{safeDetails(entry.details)}</div>}
              {timeline.length > 0 && (
                <>
                  <div className="release-log-timeline-header">
                    <button type="button" className="ghost" onClick={() => toggleTimeline(entry.id)}>
                      {isExpanded ? "Hide steps" : `View steps (${timeline.length})`}
                    </button>
                    {!isExpanded && timeline.length > visibleTimeline.length && (
                      <small>Showing first {visibleTimeline.length} steps</small>
                    )}
                  </div>
                  <ul className="release-log-timeline">
                    {visibleTimeline.map((step, index) => {
                      const stepTimestamp = step.timestamp ?? step.startedAt ?? step.endedAt;
                      return (
                        <li key={`${entry.id}-${step.name}-${index}`} className={`release-log-status ${step.status}`}>
                          <span className="status-dot">●</span>
                          <div>
                            <span>{step.name}</span>
                            <small>{formatStatusLabel(step.status)}</small>
                          </div>
                          {stepTimestamp && (
                            <span className="timeline-timestamp">
                              {new Date(stepTimestamp).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                            </span>
                          )}
                          {step.details && <span className="timeline-details">{safeDetails(step.details)}</span>}
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
