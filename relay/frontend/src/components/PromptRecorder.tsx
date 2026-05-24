/**
 * High-fidelity prompt capture widget that records keystrokes, pauses, and
 * edit snapshots before dispatching to the backend chat API.
 */
// @tag: frontend,component,prompt

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent
} from "react";
import { postChat } from "../lib/api";
import { estimateTokens } from "../lib/text";
import type {
  ArtifactRecord,
  ChatPayload,
  EditSnapshot,
  KeystrokeEvent,
  PauseEvent
} from "../types";
const INACTIVITY_THRESHOLD_MS = 700;
const SNAPSHOT_INTERVAL_MS = 1500;

/**
 * Capture text + telemetry with consistent timing semantics so submission code
 * can stay lean.
 */
function usePromptRecorder(initialValue = "") {
  const [prompt, setPrompt] = useState(initialValue);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const keystrokes = useRef<KeystrokeEvent[]>([]);
  const pauseEvents = useRef<PauseEvent[]>([]);
  const editHistory = useRef<EditSnapshot[]>([]);
  const pauseTimer = useRef<number | null>(null);
  const pauseStart = useRef<number | null>(null);
  const lastSnapshotValue = useRef<string>(initialValue);

  const recordKeystroke = useCallback((event: KeystrokeEvent) => {
    if (!startedAt) {
      setStartedAt(Date.now());
    }
    keystrokes.current.push(event);
  }, [startedAt]);

  const finalizePause = useCallback((now: number) => {
    if (pauseStart.current !== null) {
      const duration = now - pauseStart.current;
      if (duration > 0) {
        pauseEvents.current.push({
          start_timestamp_ms: pauseStart.current,
          duration_ms: duration
        });
      }
      pauseStart.current = null;
    }
  }, []);

  const schedulePauseDetection = useCallback(() => {
    if (pauseTimer.current) {
      window.clearTimeout(pauseTimer.current);
    }
    pauseTimer.current = window.setTimeout(() => {
      pauseStart.current = Date.now();
    }, INACTIVITY_THRESHOLD_MS);
  }, []);

  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLTextAreaElement>) => {
    const now = Date.now();
    recordKeystroke({ key: event.key, code: event.code, timestamp_ms: now });
    finalizePause(now);
    schedulePauseDetection();
  }, [finalizePause, recordKeystroke, schedulePauseDetection]);

  const handleChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(event.target.value);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (prompt && prompt !== lastSnapshotValue.current) {
        editHistory.current.push({ timestamp_ms: Date.now(), text: prompt });
        lastSnapshotValue.current = prompt;
      }
    }, SNAPSHOT_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [prompt]);

  const reset = useCallback(() => {
    setPrompt("");
    setStartedAt(null);
    keystrokes.current = [];
    pauseEvents.current = [];
    editHistory.current = [];
    lastSnapshotValue.current = "";
    pauseStart.current = null;
    if (pauseTimer.current) {
      window.clearTimeout(pauseTimer.current);
    }
  }, []);

  return {
    prompt,
    setPrompt,
    handleKeyDown,
    handleChange,
    keystrokes,
    pauseEvents,
    editHistory,
    startedAt,
    finalizePause,
    reset
  };
}

export interface InteractionCompleteArgs {
  payload: ChatPayload;
  responseText: string;
  interactionId: string;
  modelName?: string;
}

interface PromptRecorderProps {
  onInteractionComplete?: (args: InteractionCompleteArgs) => void;
  artifactSuggestions?: ArtifactRecord[];
}

export default function PromptRecorder({ onInteractionComplete, artifactSuggestions = [] }: PromptRecorderProps) {
  const {
    prompt,
    setPrompt,
    handleKeyDown,
    handleChange,
    keystrokes,
    pauseEvents,
    editHistory,
    startedAt,
    finalizePause,
    reset
  } = usePromptRecorder("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const tokenEstimate = useMemo(() => estimateTokens(prompt), [prompt]);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt first.");
      return;
    }
    const now = Date.now();
    finalizePause(now);
    const payload: ChatPayload = {
      final_prompt_text: prompt,
      total_duration_ms: startedAt ? now - startedAt : 0,
      token_estimate: tokenEstimate,
      keystroke_events: keystrokes.current,
      pause_events: pauseEvents.current,
      edit_history: editHistory.current,
      session_id: crypto.randomUUID(),
      ui_version: "web-0.1",
      model_hint: undefined
    };

    try {
      setIsSubmitting(true);
      setError(null);
      setStatusMessage("Streaming response…");
      const result = await postChat(payload);
      const responseText: string = result.ai_response_text ?? "No response returned.";
      onInteractionComplete?.({
        payload,
        responseText,
        interactionId: result.interaction_id ?? crypto.randomUUID(),
        modelName: result.model_name
      });
      setStatusMessage("Delivered to ChatAI");
      reset();
    } catch (submissionError) {
      const message = submissionError instanceof Error ? submissionError.message : "Unknown error";
      setError(message);
      setStatusMessage(null);
    } finally {
      setIsSubmitting(false);
      setTimeout(() => setStatusMessage(null), 1500);
    }
  }, [prompt, finalizePause, startedAt, tokenEstimate, keystrokes, pauseEvents, editHistory, reset, onInteractionComplete]);

  const handleArtifactInsert = useCallback(
    (artifact: ArtifactRecord) => {
      setPrompt((prev) => `${prev}${prev ? "\n\n" : ""}${artifact.body}`);
      setStatusMessage(`Inserted · ${artifact.title}`);
      setTimeout(() => setStatusMessage(null), 1800);
    },
    [setPrompt]
  );

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Prompt composer</h2>
        <button type="button" className="primary" onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send to ChatAI"}
        </button>
      </div>

      <div className="prompt-recorder-grid">
        <textarea
          className="prompt-input"
          placeholder="Describe the task you want help with…"
          value={prompt}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          rows={8}
        />
        {artifactSuggestions.length > 0 && (
          <aside className="prompt-artifacts">
            <p className="eyebrow">Artifact rail</p>
            <h3>Recent deposits</h3>
            <div className="artifact-chip-grid">
              {artifactSuggestions.map((artifact) => (
                <article key={artifact.id} className={`artifact-chip accent-${artifact.accent ?? "violet"}`}>
                  <header>
                    <strong>{artifact.title}</strong>
                    <span>{new Date(artifact.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </header>
                  <p>
                    {artifact.body.length > 140 ? `${artifact.body.slice(0, 140)}…` : artifact.body}
                  </p>
                  <div className="artifact-chip-actions">
                    <button type="button" className="ghost" onClick={() => handleArtifactInsert(artifact)}>
                      Insert into prompt
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </aside>
        )}
      </div>

      <div className="metrics">
        <span>Token est: {tokenEstimate}</span>
        <span>Keystrokes: {keystrokes.current.length}</span>
        <span>Pauses: {pauseEvents.current.length}</span>
        {statusMessage && <span className="status-dot">{statusMessage}</span>}
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
