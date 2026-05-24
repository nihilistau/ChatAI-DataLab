/* --------------------------------------------------------------------------
 * Component: IntegrityPanel
 * @tag:ui,integrity,ops
 * ------------------------------------------------------------------------ */
import React from "react";

interface IntegrityStatus {
  error?: string;
  files?: Array<{ path: string; hash: string; size: number; last_modified: string; tags: string[] }>;
  summary?: { total: number; modified: number; missing: number; drift: number };
}

export const IntegrityPanel: React.FC<{ integrity: IntegrityStatus | null }> = ({ integrity }) => {
  if (!integrity) return <div className="control-card">No integrity status available.</div>;
  if (integrity.error) return <div className="control-card control-card--error">{integrity.error}</div>;
  return (
    <section className="control-card">
      <header className="control-card__header">
        <h2>Integrity Checkpoint</h2>
      </header>
      <dl>
        <dt>Total Files</dt>
        <dd>{integrity.summary?.total ?? "—"}</dd>
        <dt>Modified</dt>
        <dd>{integrity.summary?.modified ?? "—"}</dd>
        <dt>Missing</dt>
        <dd>{integrity.summary?.missing ?? "—"}</dd>
        <dt>Drift</dt>
        <dd>{integrity.summary?.drift ?? "—"}</dd>
      </dl>
    </section>
  );
};
