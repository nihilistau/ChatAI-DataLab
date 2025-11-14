import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * High-fidelity prompt capture widget that records keystrokes, pauses, and
 * edit snapshots before dispatching to the backend chat API.
 */
// @tag: frontend,component,prompt
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { postChat } from "../lib/api";
import { estimateTokens } from "../lib/text";
const INACTIVITY_THRESHOLD_MS = 700;
const SNAPSHOT_INTERVAL_MS = 1500;
/**
 * Capture text + telemetry with consistent timing semantics so submission code
 * can stay lean.
 */
function usePromptRecorder(initialValue = "") {
    const [prompt, setPrompt] = useState(initialValue);
    const [startedAt, setStartedAt] = useState(null);
    const keystrokes = useRef([]);
    const pauseEvents = useRef([]);
    const editHistory = useRef([]);
    const pauseTimer = useRef(null);
    const pauseStart = useRef(null);
    const lastSnapshotValue = useRef(initialValue);
    const recordKeystroke = useCallback((event) => {
        if (!startedAt) {
            setStartedAt(Date.now());
        }
        keystrokes.current.push(event);
    }, [startedAt]);
    const finalizePause = useCallback((now) => {
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
    const handleKeyDown = useCallback((event) => {
        const now = Date.now();
        recordKeystroke({ key: event.key, code: event.code, timestamp_ms: now });
        finalizePause(now);
        schedulePauseDetection();
    }, [finalizePause, recordKeystroke, schedulePauseDetection]);
    const handleChange = useCallback((event) => {
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
export default function PromptRecorder({ onInteractionComplete, artifactSuggestions = [] }) {
    const { prompt, setPrompt, handleKeyDown, handleChange, keystrokes, pauseEvents, editHistory, startedAt, finalizePause, reset } = usePromptRecorder("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [statusMessage, setStatusMessage] = useState(null);
    const tokenEstimate = useMemo(() => estimateTokens(prompt), [prompt]);
    const handleSubmit = useCallback(async () => {
        if (!prompt.trim()) {
            setError("Please enter a prompt first.");
            return;
        }
        const now = Date.now();
        finalizePause(now);
        const payload = {
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
            const responseText = result.ai_response_text ?? "No response returned.";
            onInteractionComplete?.({
                payload,
                responseText,
                interactionId: result.interaction_id ?? crypto.randomUUID(),
                modelName: result.model_name
            });
            setStatusMessage("Delivered to ChatAI");
            reset();
        }
        catch (submissionError) {
            const message = submissionError instanceof Error ? submissionError.message : "Unknown error";
            setError(message);
            setStatusMessage(null);
        }
        finally {
            setIsSubmitting(false);
            setTimeout(() => setStatusMessage(null), 1500);
        }
    }, [prompt, finalizePause, startedAt, tokenEstimate, keystrokes, pauseEvents, editHistory, reset, onInteractionComplete]);
    const handleArtifactInsert = useCallback((artifact) => {
        setPrompt((prev) => `${prev}${prev ? "\n\n" : ""}${artifact.body}`);
        setStatusMessage(`Inserted · ${artifact.title}`);
        setTimeout(() => setStatusMessage(null), 1800);
    }, [setPrompt]);
    return (_jsxs("section", { className: "panel", children: [_jsxs("div", { className: "panel-header", children: [_jsx("h2", { children: "Prompt composer" }), _jsx("button", { type: "button", className: "primary", onClick: handleSubmit, disabled: isSubmitting, children: isSubmitting ? "Sending…" : "Send to ChatAI" })] }), _jsxs("div", { className: "prompt-recorder-grid", children: [_jsx("textarea", { className: "prompt-input", placeholder: "Describe the task you want help with\u2026", value: prompt, onChange: handleChange, onKeyDown: handleKeyDown, rows: 8 }), artifactSuggestions.length > 0 && (_jsxs("aside", { className: "prompt-artifacts", children: [_jsx("p", { className: "eyebrow", children: "Artifact rail" }), _jsx("h3", { children: "Recent deposits" }), _jsx("div", { className: "artifact-chip-grid", children: artifactSuggestions.map((artifact) => (_jsxs("article", { className: `artifact-chip accent-${artifact.accent ?? "violet"}`, children: [_jsxs("header", { children: [_jsx("strong", { children: artifact.title }), _jsx("span", { children: new Date(artifact.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) })] }), _jsx("p", { children: artifact.body.length > 140 ? `${artifact.body.slice(0, 140)}…` : artifact.body }), _jsx("div", { className: "artifact-chip-actions", children: _jsx("button", { type: "button", className: "ghost", onClick: () => handleArtifactInsert(artifact), children: "Insert into prompt" }) })] }, artifact.id))) })] }))] }), _jsxs("div", { className: "metrics", children: [_jsxs("span", { children: ["Token est: ", tokenEstimate] }), _jsxs("span", { children: ["Keystrokes: ", keystrokes.current.length] }), _jsxs("span", { children: ["Pauses: ", pauseEvents.current.length] }), statusMessage && _jsx("span", { className: "status-dot", children: statusMessage })] }), error && _jsx("p", { className: "error", children: error })] }));
}
