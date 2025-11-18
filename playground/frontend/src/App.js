import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * Root UI shell for ChatAI · DataLab, orchestrating the Ops deck, canvas,
 * telemetry thread, and instrumentation hooks.
 */
// @tag: frontend,app,shell
import { useCallback, useEffect, useMemo, useState } from "react";
import CanvasBoard from "./components/CanvasBoard";
import ConversationThread from "./components/ConversationThread";
import PromptRecorder from "./components/PromptRecorder";
import ArtifactsShelf from "./components/ArtifactsShelf";
import TailLogCell from "./components/TailLogCell";
import SearchTelemetryCard from "./components/SearchTelemetryCard";
import OpsDeck from "./components/OpsDeck";
import WidgetShowcase from "./components/design-system/WidgetShowcase";
import { createArtifact, createTailLogEntry, fetchArtifacts, fetchOpsStatus, fetchTailLog, sendOpsCommand } from "./lib/api";
import { estimateTokens } from "./lib/text";
const initialMessages = [
    {
        id: crypto.randomUUID(),
        role: "system",
        content: "Welcome to ChatAI · DataLab. Every prompt here is fully instrumented—typing cadence, pauses, edit history, the works.",
        timestamp: Date.now()
    }
];
const initialCanvas = [
    {
        id: crypto.randomUUID(),
        owner: "user",
        title: "Hypothesis · Pause density",
        body: "Capture typing telemetry to correlate pause clusters with prompt quality deltas.",
        accent: "lime",
        category: "hypothesis",
        updatedAt: Date.now() - 1000 * 60 * 60
    },
    {
        id: crypto.randomUUID(),
        owner: "user",
        title: "Hypothesis · Token priming",
        body: "Front-load intent framing to reduce follow-up clarifications by 20%.",
        accent: "forest",
        category: "hypothesis",
        updatedAt: Date.now() - 1000 * 40
    },
    {
        id: crypto.randomUUID(),
        owner: "shared",
        title: "Rhythm tracker",
        body: "Live workspace capturing cadence metrics and guardrails.",
        accent: "peach",
        category: "insight",
        updatedAt: Date.now()
    },
    {
        id: crypto.randomUUID(),
        owner: "assistant",
        title: "Model Notes",
        body: "ChatAI drops quick summaries, metrics, and follow-ups here.",
        accent: "forest",
        category: "insight",
        updatedAt: Date.now() - 1000 * 15
    }
];
const OPS_POLL_INTERVAL_MS = 25000;
const THEME_VARIANTS = [
    {
        key: "midnight",
        title: "Midnight control",
        blurb: "Deep navy glass with neon lime telemetry – the hacker default.",
        chips: ["default", "ops", "neon"],
        metric: "Balanced"
    },
    {
        key: "slate",
        title: "Slate studio",
        blurb: "Soft charcoal with electric violet seams for calm monitoring.",
        chips: ["calm", "product", "violet"],
        metric: "Zen"
    },
    {
        key: "forge",
        title: "Forge array",
        blurb: "Molten amber gradients plus rugged industrial type.",
        chips: ["amber", "grid", "ops"],
        metric: "Aggressive"
    },
    {
        key: "neon-lab",
        title: "Neon lab",
        blurb: "Vivid teal + magenta split-tone tuned for demonstrations.",
        chips: ["demo", "bright", "lab"],
        metric: "Showcase"
    }
];
/**
 * Compose the end-to-end operator experience: fetch shared data, wire
 * interaction callbacks, and render each instrumentation surface.
 */
function App() {
    const [themeKey, setThemeKey] = useState(() => {
        if (typeof window === "undefined")
            return THEME_VARIANTS[0].key;
        const stored = window.localStorage.getItem("playground.theme");
        return stored && THEME_VARIANTS.some((theme) => theme.key === stored) ? stored : THEME_VARIANTS[0].key;
    });
    const [messages, setMessages] = useState(initialMessages);
    const [canvasItems, setCanvasItems] = useState(initialCanvas);
    const [artifactItems, setArtifactItems] = useState([]);
    const [tailLog, setTailLog] = useState([]);
    const [opsStatus, setOpsStatus] = useState(null);
    const [opsBusyAction, setOpsBusyAction] = useState(null);
    const [opsError, setOpsError] = useState(null);
    const [opsLastSync, setOpsLastSync] = useState(null);
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const [artifacts, entries] = await Promise.all([fetchArtifacts(), fetchTailLog()]);
                if (!cancelled) {
                    setArtifactItems(artifacts);
                    setTailLog(entries);
                }
            }
            catch (error) {
                console.warn("Bootstrap fetch failed", error);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);
    const refreshOpsStatus = useCallback(async () => {
        try {
            const snapshot = await fetchOpsStatus();
            setOpsStatus(snapshot);
            setOpsError(null);
            setOpsLastSync(Date.now());
        }
        catch (error) {
            const message = error instanceof Error ? error.message : "Failed to load ops status";
            setOpsError(message);
        }
    }, []);
    useEffect(() => {
        refreshOpsStatus();
        const handle = window.setInterval(refreshOpsStatus, OPS_POLL_INTERVAL_MS);
        return () => window.clearInterval(handle);
    }, [refreshOpsStatus]);
    useEffect(() => {
        if (typeof document !== "undefined") {
            document.body.dataset.theme = themeKey;
        }
        if (typeof window !== "undefined") {
            window.localStorage.setItem("playground.theme", themeKey);
        }
    }, [themeKey]);
    const appendTailLog = useCallback(async (message, source = "system") => {
        try {
            const entry = await createTailLogEntry({ message, source });
            setTailLog((prev) => [entry, ...prev].slice(0, 18));
        }
        catch (error) {
            console.warn("Failed to persist tail log", error);
            setTailLog((prev) => [
                { id: crypto.randomUUID(), message, source, createdAt: Date.now() },
                ...prev
            ].slice(0, 18));
        }
    }, []);
    const handleThemeSelect = useCallback((key) => {
        if (key === themeKey)
            return;
        setThemeKey(key);
        appendTailLog(`ui · theme switched → ${key}`, "ui");
    }, [appendTailLog, themeKey]);
    const handleOpsCommand = useCallback(async (action, target) => {
        setOpsBusyAction(action);
        try {
            const response = await sendOpsCommand({ action, target });
            await appendTailLog(`ops · ${response.action} → ${response.target} (${response.runtime ?? "auto"})`, "ops");
            await refreshOpsStatus();
        }
        catch (error) {
            const message = error instanceof Error ? error.message : "Ops command failed";
            setOpsError(message);
            await appendTailLog(`ops · ${action} failed — ${message}`, "ops");
        }
        finally {
            setOpsBusyAction(null);
        }
    }, [appendTailLog, refreshOpsStatus]);
    const handleInteractionComplete = useCallback(({ payload, responseText, interactionId, modelName }) => {
        setMessages((prev) => [
            ...prev,
            {
                id: `${interactionId}-user`,
                role: "user",
                content: payload.final_prompt_text,
                timestamp: Date.now(),
                tokenEstimate: payload.token_estimate
            },
            {
                id: `${interactionId}-assistant`,
                role: "assistant",
                content: responseText,
                timestamp: Date.now(),
                tokenEstimate: estimateTokens(responseText)
            }
        ]);
        setCanvasItems((prev) => [
            {
                id: interactionId,
                owner: "assistant",
                title: modelName ?? "ChatAI Response",
                body: responseText.slice(0, 160) + (responseText.length > 160 ? "…" : ""),
                accent: "peach",
                category: "insight",
                updatedAt: Date.now()
            },
            ...prev
        ]);
        appendTailLog(`chat · ${modelName ?? "assistant"} responded (${payload.token_estimate ?? 0} tokens)`, "chat");
    }, [appendTailLog]);
    const moveCanvasItem = (id, owner) => {
        setCanvasItems((prev) => prev.map((item) => (item.id === id ? { ...item, owner, updatedAt: Date.now() } : item)));
    };
    const createCanvasItem = (owner, title, body, category) => {
        if (!title.trim() || !body.trim())
            return;
        const accent = owner === "user" ? "lime" : owner === "assistant" ? "peach" : "violet";
        const card = {
            id: crypto.randomUUID(),
            owner,
            title,
            body,
            accent,
            category,
            updatedAt: Date.now()
        };
        setCanvasItems((prev) => [card, ...prev]);
        appendTailLog(`deck · Added ${category ?? "insight"} → ${title}`, "deck");
    };
    const promoteToArtifact = useCallback(async (id) => {
        const target = canvasItems.find((item) => item.id === id);
        if (!target)
            return;
        try {
            const persisted = await createArtifact({
                title: target.title,
                body: target.body,
                owner: target.owner,
                category: "artifact",
                accent: target.accent
            });
            setArtifactItems((prev) => [persisted, ...prev].slice(0, 8));
            appendTailLog(`archive · ${target.title} saved to artifacts`, "artifact");
        }
        catch (error) {
            console.error("Failed to persist artifact", error);
        }
    }, [appendTailLog, canvasItems]);
    const activeTheme = useMemo(() => THEME_VARIANTS.find((theme) => theme.key === themeKey) ?? THEME_VARIANTS[0], [themeKey]);
    const heroStats = useMemo(() => [
        { label: "Signals tracked", value: "4" },
        { label: "Hypothesis deck", value: canvasItems.filter((item) => item.category === "hypothesis").length.toString() },
        { label: "Artifacts", value: artifactItems.length.toString() }
    ], [canvasItems, artifactItems]);
    const promptArtifacts = useMemo(() => artifactItems.slice(0, 3), [artifactItems]);
    return (_jsxs("main", { className: "app-shell dark", children: [_jsxs("section", { className: "hero", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "ChatAI \u00B7 Data capture" }), _jsx("h1", { children: "Command observatory" }), _jsx("p", { className: "lead", children: activeTheme.blurb }), _jsxs("div", { className: "metrics", children: [_jsx("span", { className: "status-dot", children: "\u25CF" }), "Running ", activeTheme.title, _jsx("span", { className: "chip active", children: activeTheme.metric })] })] }), _jsx("div", { className: "hero-stats", children: heroStats.map((stat) => (_jsxs("div", { children: [_jsx("span", { children: stat.value }), _jsx("small", { children: stat.label })] }, stat.label))) })] }), _jsx("section", { className: "theme-dock", children: THEME_VARIANTS.map((theme) => (_jsxs("button", { type: "button", className: `theme-card${theme.key === themeKey ? " active" : ""}`, onClick: () => handleThemeSelect(theme.key), children: [_jsx("header", { children: _jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: theme.metric }), _jsx("h3", { children: theme.title })] }) }), _jsx("p", { children: theme.blurb }), _jsxs("div", { children: [theme.chips.map((chip) => (_jsx("span", { className: theme.key === themeKey ? "chip active" : "chip", children: chip }, `${theme.key}-${chip}`))), theme.key === themeKey && _jsx("span", { className: "chip active", children: "current" })] })] }, theme.key))) }), _jsxs("section", { className: "ops-container", children: [_jsxs("header", { className: "panel-header", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Ops orchestration" }), _jsx("h2", { children: "Hacker terminal" })] }), _jsxs("small", { children: ["Last sync \u00B7 ", opsLastSync ? new Date(opsLastSync).toLocaleTimeString() : "pending"] })] }), _jsx("p", { className: "lead", children: "Live service states, psutil telemetry, and workflow macros wired straight into the orchestrator." }), opsError && _jsx("span", { className: "ops-error", children: opsError }), _jsx(OpsDeck, { status: opsStatus, onCommand: handleOpsCommand, busyAction: opsBusyAction })] }), _jsxs("div", { className: "workspace-grid", children: [_jsxs("section", { className: "terminal-panel", children: [_jsx("header", { className: "panel-header", children: _jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Conversation" }), _jsx("h2", { children: "Telemetry thread" })] }) }), _jsx(ConversationThread, { messages: messages }), _jsx(PromptRecorder, { onInteractionComplete: handleInteractionComplete, artifactSuggestions: promptArtifacts })] }), _jsxs("div", { className: "intel-stack", children: [_jsx(SearchTelemetryCard, {}), _jsx(TailLogCell, { entries: tailLog })] })] }), _jsxs("section", { className: "canvas-expanse", children: [_jsx("header", { className: "panel-header", children: _jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Canvas architecture" }), _jsx("h2", { children: "Hypotheses \u00B7 Signals \u00B7 Notes" })] }) }), _jsx(CanvasBoard, { items: canvasItems, onMove: moveCanvasItem, onCreate: createCanvasItem, onPromoteToArtifact: promoteToArtifact })] }), _jsx(ArtifactsShelf, { artifacts: artifactItems }), _jsx(WidgetShowcase, {})] }));
}
export default App;
