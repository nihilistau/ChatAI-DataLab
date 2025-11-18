/**
 * Root UI shell for ChatAI · DataLab, orchestrating the Ops deck, canvas,
 * telemetry thread, and instrumentation hooks.
 */
// @tag: frontend,app,shell

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CanvasBoard from "./components/CanvasBoard";
import ConversationThread from "./components/ConversationThread";
import PromptRecorder, { InteractionCompleteArgs } from "./components/PromptRecorder";
import ArtifactsShelf from "./components/ArtifactsShelf";
import TailLogCell from "./components/TailLogCell";
import SearchTelemetryCard from "./components/SearchTelemetryCard";
import OpsDeck from "./components/OpsDeck";
import WidgetShowcase from "./components/design-system/WidgetShowcase";
import ManifestLayoutPreview from "./components/ManifestLayoutPreview";
import ManifestWidgetSummary from "./components/ManifestWidgetSummary";
import {
  createArtifact,
  createTailLogEntry,
  fetchArtifacts,
  fetchOpsStatus,
  fetchTailLog,
  sendOpsCommand
} from "./lib/api";
import { useManifest } from "./context/ManifestContext";
import { estimateTokens } from "./lib/text";
import type {
  ArtifactRecord,
  CanvasItem,
  ConversationMessage,
  OpsAction,
  OpsStatus,
  TailLogEntry
} from "./types";

const initialMessages: ConversationMessage[] = [
  {
    id: crypto.randomUUID(),
    role: "system",
    content: "Welcome to ChatAI · DataLab. Every prompt here is fully instrumented—typing cadence, pauses, edit history, the works.",
    timestamp: Date.now()
  }
];

const initialCanvas: CanvasItem[] = [
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

type ThemeVariant = {
  key: string;
  title: string;
  blurb: string;
  chips: string[];
  metric: string;
};

const THEME_VARIANTS: ThemeVariant[] = [
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
  const [themeKey, setThemeKey] = useState<string>(() => {
    if (typeof window === "undefined") return THEME_VARIANTS[0].key;
    const stored = window.localStorage.getItem("playground.theme");
    return stored && THEME_VARIANTS.some((theme) => theme.key === stored) ? stored : THEME_VARIANTS[0].key;
  });
  const [messages, setMessages] = useState<ConversationMessage[]>(initialMessages);
  const [canvasItems, setCanvasItems] = useState<CanvasItem[]>(initialCanvas);
  const [artifactItems, setArtifactItems] = useState<ArtifactRecord[]>([]);
  const [tailLog, setTailLog] = useState<TailLogEntry[]>([]);
  const [opsStatus, setOpsStatus] = useState<OpsStatus | null>(null);
  const [opsBusyAction, setOpsBusyAction] = useState<OpsAction | null>(null);
  const [opsError, setOpsError] = useState<string | null>(null);
  const [opsLastSync, setOpsLastSync] = useState<number | null>(null);
  const {
    manifest,
    loading: manifestLoading,
    error: manifestError,
    status: manifestStatus,
    tenant: manifestTenant,
    playground: manifestPlayground,
    refresh: refreshManifest,
    refreshing: manifestRefreshing,
    autoRefreshEnabled,
    setAutoRefreshEnabled,
    lastFetched: manifestLastFetched
  } = useManifest();
  const manifestSyncChecksum = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [artifacts, entries] = await Promise.all([fetchArtifacts(), fetchTailLog()]);
        if (!cancelled) {
          setArtifactItems(artifacts);
          setTailLog(entries);
        }
      } catch (error) {
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
    } catch (error) {
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

  const appendTailLog = useCallback(
    async (message: string, source = "system") => {
      try {
        const entry = await createTailLogEntry({ message, source });
        setTailLog((prev) => [entry, ...prev].slice(0, 18));
      } catch (error) {
        console.warn("Failed to persist tail log", error);
        setTailLog((prev) => [
          { id: crypto.randomUUID(), message, source, createdAt: Date.now() },
          ...prev
        ].slice(0, 18));
      }
    },
    []
  );

  useEffect(() => {
    if (!manifest) return;
    if (manifestSyncChecksum.current === manifest.checksum) return;
    manifestSyncChecksum.current = manifest.checksum;
    appendTailLog(`manifest · ${manifest.playground} rev ${manifest.revision} synced`, "manifest");
  }, [appendTailLog, manifest]);

  

  const handleThemeSelect = useCallback(
    (key: string) => {
      if (key === themeKey) return;
      setThemeKey(key);
      appendTailLog(`ui · theme switched → ${key}`, "ui");
    },
    [appendTailLog, themeKey]
  );

  const handleOpsCommand = useCallback(
    async (action: OpsAction, target?: string) => {
      setOpsBusyAction(action);
      try {
        const response = await sendOpsCommand({ action, target });
        await appendTailLog(
          `ops · ${response.action} → ${response.target} (${response.runtime ?? "auto"})`,
          "ops"
        );
        await refreshOpsStatus();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Ops command failed";
        setOpsError(message);
        await appendTailLog(`ops · ${action} failed — ${message}`, "ops");
      } finally {
        setOpsBusyAction(null);
      }
    },
    [appendTailLog, refreshOpsStatus]
  );

  const handleInteractionComplete = useCallback(({
    payload,
    responseText,
    interactionId,
    modelName
  }: InteractionCompleteArgs) => {
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

  const moveCanvasItem = (id: string, owner: CanvasItem["owner"]) => {
    setCanvasItems((prev) => prev.map((item) => (item.id === id ? { ...item, owner, updatedAt: Date.now() } : item)));
  };

  const createCanvasItem = (
    owner: CanvasItem["owner"],
    title: string,
    body: string,
    category: CanvasItem["category"]
  ) => {
    if (!title.trim() || !body.trim()) return;
    const accent = owner === "user" ? "lime" : owner === "assistant" ? "peach" : "violet";
    const card: CanvasItem = {
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

  const promoteToArtifact = useCallback(
    async (id: string) => {
      const target = canvasItems.find((item) => item.id === id);
      if (!target) return;

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
      } catch (error) {
        console.error("Failed to persist artifact", error);
      }
    },
    [appendTailLog, canvasItems]
  );

  const activeTheme = useMemo(
    () => THEME_VARIANTS.find((theme) => theme.key === themeKey) ?? THEME_VARIANTS[0],
    [themeKey]
  );

  const heroStats = useMemo(
    () => [
      { label: "Signals tracked", value: "4" },
      { label: "Hypothesis deck", value: canvasItems.filter((item) => item.category === "hypothesis").length.toString() },
      { label: "Artifacts", value: artifactItems.length.toString() }
    ],
    [canvasItems, artifactItems]
  );

  const promptArtifacts = useMemo(() => artifactItems.slice(0, 3), [artifactItems]);

  return (
    <main className="app-shell dark">
      <section className="hero">
        <div>
          <p className="eyebrow">ChatAI · Data capture</p>
          <h1>Command observatory</h1>
          <p className="lead">{activeTheme.blurb}</p>
          <div className="metrics">
            <span className="status-dot">●</span>
            Running {activeTheme.title}
            <span className="chip active">{activeTheme.metric}</span>
          </div>
        </div>
        <div className="hero-stats">
          {heroStats.map((stat) => (
            <div key={stat.label}>
              <span>{stat.value}</span>
              <small>{stat.label}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="manifest-panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Playground manifest</p>
            <h2>Kitchen ↔ Control surface</h2>
          </div>
          <div className="panel-controls">
            <small>
              {manifestTenant}/{manifestPlayground}
            </small>
            <div className="manifest-controls">
              <button type="button" onClick={() => refreshManifest()} disabled={manifestRefreshing}>
                {manifestRefreshing ? "Refreshing…" : "Refresh"}
              </button>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={autoRefreshEnabled}
                  onChange={(event) => setAutoRefreshEnabled(event.target.checked)}
                />
                Auto refresh
              </label>
            </div>
            {manifestLastFetched && (
              <small className="timestamp">Synced {new Date(manifestLastFetched).toLocaleTimeString()}</small>
            )}
          </div>
        </header>
        <p className="lead">Latest layout published from the Kitchen. Update the Welcome Cookbook to refresh this preview.</p>
        {manifestLoading && <p className="text-muted">Loading latest manifest…</p>}
        {!manifestLoading && manifest && <ManifestLayoutPreview manifest={manifest} />}
        {!manifestLoading && !manifest && !manifestError && manifestStatus && (
          <p className="text-muted">{manifestStatus}</p>
        )}
        {manifestError && <span className="error">{manifestError}</span>}
      </section>

      <section className="theme-dock">
        {THEME_VARIANTS.map((theme) => (
          <button
            type="button"
            key={theme.key}
            className={`theme-card${theme.key === themeKey ? " active" : ""}`}
            onClick={() => handleThemeSelect(theme.key)}
          >
            <header>
              <div>
                <p className="eyebrow">{theme.metric}</p>
                <h3>{theme.title}</h3>
              </div>
            </header>
            <p>{theme.blurb}</p>
            <div>
              {theme.chips.map((chip) => (
                <span key={`${theme.key}-${chip}`} className={theme.key === themeKey ? "chip active" : "chip"}>
                  {chip}
                </span>
              ))}
              {theme.key === themeKey && <span className="chip active">current</span>}
            </div>
          </button>
        ))}
      </section>

      <section className="ops-container">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Ops orchestration</p>
            <h2>Hacker terminal</h2>
          </div>
          <small>Last sync · {opsLastSync ? new Date(opsLastSync).toLocaleTimeString() : "pending"}</small>
        </header>
        <p className="lead">Live service states, psutil telemetry, and workflow macros wired straight into the orchestrator.</p>
        {opsError && <span className="ops-error">{opsError}</span>}
        <OpsDeck status={opsStatus} onCommand={handleOpsCommand} busyAction={opsBusyAction} />
      </section>

      <div className="workspace-grid">
        <section className="terminal-panel">
          <header className="panel-header">
            <div>
              <p className="eyebrow">Conversation</p>
              <h2>Telemetry thread</h2>
            </div>
          </header>
          <ConversationThread messages={messages} />
          <PromptRecorder onInteractionComplete={handleInteractionComplete} artifactSuggestions={promptArtifacts} />
        </section>

        <div className="intel-stack">
          <SearchTelemetryCard />
          <ManifestWidgetSummary />
          <TailLogCell entries={tailLog} />
        </div>
      </div>

      <section className="canvas-expanse">
        <header className="panel-header">
          <div>
            <p className="eyebrow">Canvas architecture</p>
            <h2>Hypotheses · Signals · Notes</h2>
          </div>
        </header>
        <CanvasBoard
          items={canvasItems}
          onMove={moveCanvasItem}
          onCreate={createCanvasItem}
          onPromoteToArtifact={promoteToArtifact}
        />
      </section>

      <ArtifactsShelf artifacts={artifactItems} />

      <WidgetShowcase />
    </main>
  );
}

export default App;
