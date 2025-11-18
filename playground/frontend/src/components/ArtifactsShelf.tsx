/**
 * Compact rail that showcases persisted artifacts for quick recall.
 */
// @tag: frontend,component,artifacts

import type { ArtifactRecord } from "../types";

interface ArtifactsShelfProps {
  artifacts: ArtifactRecord[];
  onSelect?: (artifact: ArtifactRecord) => void;
}

export default function ArtifactsShelf({ artifacts, onSelect }: ArtifactsShelfProps) {
  /**
   * Render the shelf inline when artifacts exist; otherwise stay hidden to
   * reduce chrome.
   */
  if (!artifacts.length) {
    return null;
  }

  return (
    <section className="artifacts-shelf">
      <header className="panel-header">
        <div>
          <p className="eyebrow">Artifacts rail</p>
          <h2>Persistent evidence locker</h2>
        </div>
      </header>
      <div className="artifact-rail">
        {artifacts.map((artifact) => (
          <article key={artifact.id} className={`artifact-card accent-${artifact.accent ?? "violet"}`}>
            <div className="artifact-headline">
              <h3>{artifact.title}</h3>
              <span>{new Date(artifact.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            </div>
            <p>{artifact.body}</p>
            {onSelect && (
              <div className="artifact-actions">
                <button type="button" className="ghost" onClick={() => onSelect(artifact)}>
                  Insert
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
