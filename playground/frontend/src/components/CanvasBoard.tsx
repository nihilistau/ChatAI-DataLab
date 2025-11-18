/**
 * Drag-and-drop canvas that tracks hypotheses, shared cards, and assistant
 * insights for the operator workspace.
 */
// @tag: frontend,component,canvas

import { useMemo, useState } from "react";
import type { DragEvent, FormEvent } from "react";
import type { CanvasCategory, CanvasItem, CanvasOwner } from "../types";

interface CanvasBoardProps {
  items: CanvasItem[];
  onMove: (id: string, owner: CanvasOwner) => void;
  onCreate: (owner: CanvasOwner, title: string, body: string, category?: CanvasCategory) => void;
  onPromoteToArtifact: (id: string) => void;
}

const sharedColumns: { owner: CanvasOwner; title: string; hint: string }[] = [
  { owner: "shared", title: "Shared Canvas", hint: "Live collaboration" },
  { owner: "assistant", title: "ChatAI Desk", hint: "Autonomous notes" }
];

const ownerOptions: { label: string; value: CanvasOwner; helper: string }[] = [
  { label: "User", value: "user", helper: "Hypothesis" },
  { label: "Shared", value: "shared", helper: "Signal" },
  { label: "ChatAI", value: "assistant", helper: "Insight" }
];

const categoryOptions: { value: CanvasCategory; label: string }[] = [
  { value: "hypothesis", label: "Hypothesis" },
  { value: "insight", label: "Insight" },
  { value: "signal", label: "Signal" }
];

export default function CanvasBoard({ items, onMove, onCreate, onPromoteToArtifact }: CanvasBoardProps) {
  /**
   * Local composer state mirrors the column selections so the UX stays
   * keyboard-friendly without extra context providers.
   */
  const [composerOwner, setComposerOwner] = useState<CanvasOwner>("user");
  const [composerCategory, setComposerCategory] = useState<CanvasCategory>("hypothesis");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const grouped = useMemo(() => {
    return items.reduce<Record<CanvasOwner, CanvasItem[]>>(
      (acc, item) => {
        acc[item.owner].push(item);
        return acc;
      },
      { user: [], shared: [], assistant: [] }
    );
  }, [items]);

  const hypotheses = grouped.user.filter((item) => item.category === "hypothesis");

  const handleDragStart = (event: DragEvent<HTMLElement>, id: string) => {
    event.dataTransfer.setData("text/plain", id);
  };

  const handleDrop = (event: DragEvent<HTMLElement>, owner: CanvasOwner) => {
    const id = event.dataTransfer.getData("text/plain");
    if (id) {
      onMove(id, owner);
    }
    event.preventDefault();
  };

  const allowDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onCreate(composerOwner, title, body, composerCategory);
    setTitle("");
    setBody("");
  };

  return (
    <section className="canvas-board">
      <div className="deck-panel" onDrop={(event) => handleDrop(event, "user")} onDragOver={allowDrop}>
        <header>
          <h3>Hypothesis deck</h3>
          <p>Portfolio of the current bets and assumptions.</p>
        </header>
        <div className="deck-cards">
          {hypotheses.length === 0 && <div className="empty-state">Drop a hypothesis to seed the deck</div>}
          {hypotheses.map((item) => (
            <article
              key={item.id}
              className={`deck-card accent-${item.accent ?? "lime"}`}
              draggable
              onDragStart={(event) => handleDragStart(event, item.id)}
            >
              <div className="card-meta">
                <span>{new Date(item.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                <small>{item.category}</small>
              </div>
              <h4>{item.title}</h4>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
        <form className="canvas-composer" onSubmit={handleSubmit}>
          <div className="segmented-control">
            {ownerOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={composerOwner === option.value ? "segment active" : "segment"}
                onClick={() => {
                  setComposerOwner(option.value);
                  if (option.value === "user") {
                    setComposerCategory("hypothesis");
                  } else if (composerCategory === "hypothesis") {
                    setComposerCategory("insight");
                  }
                }}
              >
                <strong>{option.label}</strong>
                <span>{option.helper}</span>
              </button>
            ))}
          </div>
          <div className="composer-fields">
            <select value={composerCategory} onChange={(event) => setComposerCategory(event.currentTarget.value as CanvasCategory)}>
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Title"
              value={title}
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
            <textarea
              placeholder="Describe the signal, hypothesis, or instruction"
              value={body}
              onChange={(event) => setBody(event.currentTarget.value)}
            />
            <div className="composer-actions">
              <button type="submit" className="primary">
                Publish card
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="board-grid">
        {sharedColumns.map((column) => (
          <div
            key={column.owner}
            className="canvas-column"
            onDrop={(event) => handleDrop(event, column.owner)}
            onDragOver={allowDrop}
          >
            <header>
              <h3>{column.title}</h3>
              <p>{column.hint}</p>
            </header>
            <div className="canvas-stack">
              {grouped[column.owner].map((item) => (
                <div
                  key={item.id}
                  className={`canvas-card accent-${item.accent ?? "lime"}`}
                  draggable
                  onDragStart={(event) => handleDragStart(event, item.id)}
                >
                  <div className="card-meta">
                    <span>{new Date(item.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    <small>{item.category ?? "note"}</small>
                  </div>
                  <h4>{item.title}</h4>
                  <p>{item.body}</p>
                  <div className="card-actions">
                    <button type="button" className="ghost" onClick={() => onPromoteToArtifact(item.id)}>
                      Artifact
                    </button>
                  </div>
                </div>
              ))}
              {grouped[column.owner].length === 0 && <div className="empty-state">Drop cards here</div>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
