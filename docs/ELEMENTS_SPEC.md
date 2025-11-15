# Elements System Scope & Architecture

> **Last updated:** 2025-11-15

The Elements initiative introduces a modular widget system plus a drag-and-drop node builder that keeps notebooks, the Control Center UI, and backend automation in sync. This document captures the scope, success criteria, and technical blueprint needed before implementation.

---

## 1. Objectives

### 1.1 Functional Goals

1. **Reusable widget primitives** that render consistently across:
   - Control Center React/Vite frontend
   - Storybook/Playground docs
   - Notebook templates (via `ipywidgets` + custom JS bridge)
2. **Graph-based workflow builder** (“Elements Canvas”) with drag/drop nodes, linking, validation, and export/import.
3. **Node execution service** that can evaluate graphs, call existing FastAPI endpoints, and orchestrate external tools (LLMs, data pulls, notebook runs).
4. **Template & preset library** so users can snap together common flows (e.g., “Ingest → Clean → Analyze → Report”).

### 1.2 Non-Functional Goals

- Maintain parity between frontend + backend definitions via a shared schema package.
- Support collaborative scenarios by persisting node graphs in Cosmos DB (or SQLite fallback) with hierarchical partition keys (`tenantId / workspaceId / graphId`).
- Pass existing CI gates (pytest, Papermill, Vitest, Storybook) and add targeted coverage for the new stack.
- Keep latency < 200 ms for UI interactions and < 2 s for small graphs executed locally.

---

## 2. Scope & Deliverables

| Area | Deliverables |
|------|--------------|
| **Design** | Component taxonomy, interaction models, theming guidelines, wiring diagram, and UX references. |
| **Frontend Elements library** | `packages/elements` (or `chatai/frontend/src/elements/`) containing: registry, props contracts, style tokens, node palette, canvas, inspector, serialization helpers, Storybook stories, unit + E2E tests. |
| **Backend node service** | FastAPI router (`/api/elements`) exposing CRUD for graphs, execution endpoint, Cosmos-friendly models, job queue adapter, guardrails for user code. |
| **Notebook templates** | At least two Papermill-tested notebooks demonstrating Elements-driven workflows and showing how to import/export graphs. |
| **Docs** | This spec, developer onboarding guide, README updates, diagram(s), and API reference snippets. |

Out of scope (future work): multi-user real-time collaboration, visual diffing, scheduled graph runs, marketplace for community nodes.

---

## 3. Architecture Overview

```
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│ Elements Registry  │◀──────▶│ Graph Canvas UI    │───────▶│ Node Execution API │
└────────────────────┘        └────────────────────┘        └────────────────────┘
         ▲                            │                             │
         │                            ▼                             ▼
┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
│ Notebook Templates │◀──────▶│ Graph Serializer    │───────▶│ Persistence Layer  │
└────────────────────┘        └────────────────────┘        └────────────────────┘
```

### Key Principles

- **Single source of truth** for node + widget definitions (TypeScript schema emitted to Python via JSON + Pydantic models).
- **Deterministic graph execution** using a DAG runner with cycle detection and typed payload contracts.
- **Extensible transport** so graphs can run locally, via background worker, or by emitting notebook cells (Papermill, Comfy-style pipelines).

---

## 4. Component Taxonomy

### 4.1 Primitives

| Category | Examples | Notes |
|----------|----------|-------|
| Layout | `Stack`, `Grid`, `Surface`, `SplitPanel` | Responsive, keyboard accessible, theme-aware. |
| Inputs | `Text`, `Code`, `Number`, `Slider`, `Toggle`, `Select`, `TagList` | Provide schema metadata + validation hooks. |
| Data | `MetricCard`, `Table`, `Timeline`, `DiffViewer`, `LLMTranscript` | Pull from graph execution context or live APIs. |
| Flow Nodes | `PromptNode`, `DatasetNode`, `TransformNode`, `NotebookNode`, `LLMNode`, `WebhookNode` | Compose into DAGs; each node maps to backend executor. |
| Utilities | `ActionBar`, `StatusPill`, `ProgressStepper` | Reused in inspector panels and templates. |

### 4.2 Shared Contracts

```ts
interface ElementDefinition {
  type: string; // e.g., "prompt", "dataset"
  version: string;
  label: string;
  icon?: string;
  inputs: Record<string, PortDefinition>;
  outputs: Record<string, PortDefinition>;
  propsSchema: JSONSchema7;
  runtime?: {
    executor: "client" | "server" | "notebook";
    handler: string; // references backend service or notebook cell id
  };
}
```

- Publish as `elements.schema.json` inside the repo; generate matching `pydantic.BaseModel` using `datamodel-code-generator` or a custom script.
- Introduce versioning for safe migrations (Semantic Versioning with `type@major.minor.patch`).

---

## 5. Node Graph Experience

### 5.1 Canvas UX

- Palette grouped by category with search + keyboard shortcuts.
- Drag/drop nodes, connect ports with deterministic snapping.
- Inspector flyout showing props form (JSON schema → dynamically built form).
- Mini-map + zoom controls for large graphs.
- Validation badges (missing required inputs, type mismatch, cycles).

### 5.2 Graph Serialization

```json
{
  "id": "graph_01HXY...",
  "tenantId": "lab",
  "workspaceId": "default",
  "name": "LLM QA Loop",
  "nodes": [
    {"id": "node_prompt", "type": "prompt", "props": {...}},
    {"id": "node_llm", "type": "llm", "props": {...}}
  ],
  "edges": [
    {"id": "edge1", "from": {"node": "node_prompt", "port": "text"}, "to": {"node": "node_llm", "port": "input"}}
  ],
  "metadata": {"tags": ["qa"], "createdBy": "nihil"}
}
```

- Use HPK = `/tenantId/workspaceId` to avoid hot partitions when stored in Cosmos DB (`graphId` becomes row key).
- Store full history (versioned snapshots) for undo/redo + auditing (append-only log or `graph_revisions` container/table).

### 5.3 Execution Contract

1. **Submit graph** → `/api/elements/graphs/{id}:execute` with optional payload overrides.
2. Service validates schema, runs topological sort, and dispatches nodes.
3. Results streamed via WebSocket (future) or polled via `/runs/{runId}`.
4. Notebook integration: convert graph to Papermill parameter file + generated notebook cells.

Edge cases to handle:
- Cycles (detect + fail fast with actionable error).
- Missing executors (unsupported node type on backend).
- Long-running tasks (async queue + status heartbeats).
- Partial failure (surface per-node diagnostics).

---

## 6. Backend Service Plan

| Item | Description |
|------|-------------|
| Router | `app/api/elements.py` with `GET/POST /graphs`, `PATCH /graphs/{id}`, `POST /graphs/{id}:execute`, `GET /runs/{runId}`. |
| Models | SQLAlchemy + Pydantic models mirroring `ElementDefinition`, `Graph`, `Node`, `Run`. |
| Storage | Start with SQLite (tables: `elements`, `graphs`, `graph_runs`), abstract via repository layer ready for Cosmos DB + HPK mapping. |
| Executors | Strategy registry keyed by `node.type`; built-in adapters for prompt orchestration, dataset fetch, Python code, notebooks, webhooks. |
| Rate limits | Basic token bucket (per tenant/workspace) + 429 responses; log diagnostics when RU thresholds hit. |
| Security | Validate user-supplied code, sandbox notebook runners, enforce allowlist for outbound webhooks. |

Testing Requirements:
- Unit tests for graph validation, serialization, executor selection.
- Integration tests covering `/graphs` CRUD + execution run lifecycle.
- Load test script (Locust) for concurrent graph executions.

---

## 7. Frontend Implementation Plan

1. **Package structure**: `chatai/frontend/src/elements/` with subfolders `components`, `nodes`, `canvas`, `hooks`, `theme`, `state`.
2. **State management**: Zustand or Redux Toolkit slice for node graphs; persist to IndexedDB for offline drafts.
3. **Canvas tech**: Evaluate `@xyflow/react`, `react-flow`, or custom D3/konva layer; wrap to enforce design tokens + accessibility.
4. **Form builder**: Auto-generate inspector forms from `propsSchema` using `react-hook-form` + `zod` for validation.
5. **Storybook**: Add MDX docs, interactive examples, Visual Regression tests (Chromatic or Playwright screenshot tests).
6. **Vitest coverage**: serialization helpers, schema utilities, Zustand actions.

---

## 8. Notebook Integration

- Provide `datalab/notebooks/elements_playground.ipynb` and `elements_reporting.ipynb` with Papermill parameters.
- Create Python module `datalab/scripts/elements.py` that can:
  - Load `elements.schema.json`.
  - Convert graph JSON into ordered execution steps.
  - Emit helper cells or run graphs entirely in Python.
- Update `tests/test_notebooks.py` to execute the new notebooks via Papermill.

---

## 9. Documentation & DX

- Update `README.md` + `docs/CONTROL_CENTER_PLAYGROUND.md` with quick-start instructions for the Elements Canvas.
- Add architecture diagram (draw.io export) + GIF demo once UI prototype exists.
- Provide API reference tables for `/api/elements/*`, including response samples + error codes.
- Ship CLI helpers (`scripts/control_center.py elements ...`) to list nodes, run graphs, and validate schema.

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema drift between TS & Python | Runtime errors, inconsistent UX | Generate shared schema from single JSON + automated tests comparing hashes. |
| Canvas performance on large graphs | Laggy UX | Virtualize node lists, throttle layout recalcs, batch state updates. |
| Long-running executions block FastAPI workers | Timeouts | Offload to background queue (RQ, Celery, or asyncio TaskGroup) with heartbeat updates. |
| Cosmos DB RU spikes | Cost & throttling | Use hierarchical partition key, batch reads/writes, honor 429 retry-after diagnostics. |
| Security of custom code nodes | Remote code execution risk | Restrict to sandboxed runtime, review uploaded code, provide allowlisted templates only. |

---

## 11. Success Criteria

- ✅ Elements library renders in Storybook with at least 5 core widgets + 3 flow nodes documented.
- ✅ Canvas supports create / edit / connect / delete / undo / redo / save / load.
- ✅ FastAPI endpoints persist graphs and run at least one end-to-end preset workflow.
- ✅ New notebooks execute via CI Papermill run without manual intervention.
- ✅ Documentation + demo assets enable contributors to create new nodes in < 30 minutes.

---

## 12. Next Steps

1. Finalize schema + shared package layout.
2. Spike React canvas using `react-flow` + design tokens.
3. Implement backend graph CRUD + executor skeletons.
4. Wire notebook helpers + Papermill tests.
5. Iterate with users to capture feedback for multi-user collaboration roadmap.
