/* --------------------------------------------------------------------------
 * Component: BugHuntPanel
 * @tag:ui,search,ops
 * ------------------------------------------------------------------------ */
import React from "react";

interface BugHuntStatus {
  error?: string;
  findings?: Array<{ pattern: string; matches: number; files: string[] }>;
}

export const BugHuntPanel: React.FC<{ bughunt: BugHuntStatus | null }> = ({ bughunt }) => {
  if (!bughunt) return <div className="control-card">No bug-hunt results available.</div>;
  if (bughunt.error) return <div className="control-card control-card--error">{bughunt.error}</div>;
  return (
    <section className="control-card">
      <header className="control-card__header">
        <h2>SearchToolkit Bug-Hunt</h2>
      </header>
      <ul>
        {bughunt.findings?.length ? (
          bughunt.findings.map((f, i) => (
            <li key={i}>
              <strong>{f.pattern}</strong>: {f.matches} matches in {f.files.length} files
            </li>
          ))
        ) : (
          <li>No suspicious patterns found.</li>
        )}
      </ul>
    </section>
  );
};
