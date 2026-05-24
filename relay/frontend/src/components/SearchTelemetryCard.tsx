import { useEffect, useMemo, useState } from "react";
import { fetchSearchTelemetrySummary } from "../lib/api";
import type { SearchTelemetrySummary, SearchPresetDrift } from "../types";

export type SearchTelemetryCardProps = {
  pollIntervalMs?: number;
};

const formatPercent = (value: number | null | undefined): string =>
  value === null || value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;

const formatNumber = (value: number | null | undefined): string =>
  value === null || value === undefined ? "—" : value.toLocaleString();

const formatDeltaPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return "0.0 pts";
  const formatted = (value * 100).toFixed(1);
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatted} pts`;
};

const statusLabelMap: Record<SearchPresetDrift["status"], string> = {
  regressing: "Regressing",
  improving: "Improving",
  stable: "Stable"
};

const statusClass = (status: SearchPresetDrift["status"]): string => {
  switch (status) {
    case "regressing":
      return "drift-status drift-status-regressing";
    case "improving":
      return "drift-status drift-status-improving";
    default:
      return "drift-status drift-status-stable";
  }
};

export default function SearchTelemetryCard({ pollIntervalMs = 60000 }: SearchTelemetryCardProps) {
  const [summary, setSummary] = useState<SearchTelemetrySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    const load = async () => {
      try {
        const snapshot = await fetchSearchTelemetrySummary();
        if (!disposed) {
          setSummary(snapshot);
          setError(null);
        }
      } catch (err) {
        if (!disposed) {
          const message = err instanceof Error ? err.message : "Failed to load search telemetry";
          setError(message);
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    };

    load();
    const handle = window.setInterval(load, pollIntervalMs);
    return () => {
      disposed = true;
      window.clearInterval(handle);
    };
  }, [pollIntervalMs]);

  const lastUpdated = useMemo(() => {
    if (!summary?.lastIngestAt) return "—";
    return new Date(summary.lastIngestAt).toLocaleString();
  }, [summary]);

  const topPatterns = summary?.topPatterns ?? [];
  const driftWatchlist = useMemo<SearchPresetDrift[]>(() => {
    if (!summary?.presetDrift) return [];
    return summary.presetDrift.slice(0, 6);
  }, [summary]);

  return (
    <section className="intel-card">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Search telemetry</p>
          <h3>Notebook-ready sweeps</h3>
        </div>
        <small>Updated · {lastUpdated}</small>
      </header>
      <p className="lead">Latest Search Toolkit runs flowing into the DataLab telemetry notebook.</p>
      {loading && <span className="text-muted">Loading telemetry…</span>}
      {error && <span className="error">{error}</span>}
      {summary && !loading && !error && (
        <>
          <div className="telemetry-metrics">
            <div>
              <span>{formatNumber(summary.totalRuns)}</span>
              <small>Total runs</small>
            </div>
            <div>
              <span>{formatNumber(summary.runsLast24h)}</span>
              <small>Last 24h</small>
            </div>
            <div>
              <span>{formatPercent(summary.matchRate)}</span>
              <small>Match rate</small>
            </div>
            <div>
              <span>{formatNumber(summary.avgDurationMs ? Math.round(summary.avgDurationMs) : null)}</span>
              <small>Avg duration (ms)</small>
            </div>
          </div>
          <div className="telemetry-top-list">
            <header>
              <p className="eyebrow">Top presets</p>
              <small>Most findings · last ingested window</small>
            </header>
            {topPatterns.length === 0 && <p className="text-muted">No presets recorded yet.</p>}
            {topPatterns.length > 0 && (
              <ol>
                {topPatterns.map((pattern) => (
                  <li key={pattern.pattern}>
                    <div>
                      <strong>{pattern.pattern}</strong>
                      <span>{pattern.totalMatches} matches</span>
                    </div>
                    <small>
                      {pattern.runs} runs · avg files scanned {Math.round(pattern.avgFilesScanned).toLocaleString()}
                    </small>
                  </li>
                ))}
              </ol>
            )}
          </div>
          <div className="telemetry-drift-board">
            <header>
              <div>
                <p className="eyebrow">Preset drift watchlist</p>
                <small>Recent {summary.presetDrift?.length ?? 0} presets · sorted by delta</small>
              </div>
            </header>
            {driftWatchlist.length === 0 && (
              <p className="text-muted">Need more runs to calculate preset drift.</p>
            )}
            {driftWatchlist.length > 0 && (
              <ul>
                {driftWatchlist.map((entry) => (
                  <li key={entry.preset}>
                    <div className="drift-row-header">
                      <strong>{entry.preset}</strong>
                      <span className={statusClass(entry.status)}>{statusLabelMap[entry.status]}</span>
                    </div>
                    <div className="drift-row-metrics">
                      <div>
                        <small>Recent</small>
                        <span>{formatPercent(entry.matchRateRecent)}</span>
                      </div>
                      <div>
                        <small>Lifetime</small>
                        <span>{formatPercent(entry.matchRateLifetime)}</span>
                      </div>
                      <div>
                        <small>Δ Match</small>
                        <span>{formatDeltaPercent(entry.deltaMatchRate)}</span>
                      </div>
                      <div>
                        <small>Recent runs</small>
                        <span>{entry.recentRuns}</span>
                      </div>
                    </div>
                    {entry.tags.length > 0 && (
                      <div className="drift-tags">
                        {entry.tags.map((tag) => (
                          <span className="tag-chip" key={tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
}
