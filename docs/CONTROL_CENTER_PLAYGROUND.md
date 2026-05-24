# Control Center + Relay System

This document captures the end-to-end design for the new automation layer that stitches together FastAPI, React/Storybook, Papermill notebooks, and the Lab Orchestrator. The goal is to provide a repeatable "mission control" experience where three long-running services stay in sync (FastAPI backend, legacy Ops Deck frontend, and the new Relay UI) while Workshop notebooks run supervised pipelines.

---

## 1. Objectives

1. **Unified launch surface** – a single CLI (`scripts/control_center.py`) that starts/stops backend, Ops Deck, Relay UI, and the Papermill runner, streaming their logs to `.labctl/logs`.
2. **Widget-first telemetry** – backend surfaces a `/api/control` namespace that exposes orchestrator snapshots, log tails, notebook runs, and synthetic scenario data for UI widgets.
3. **Relay UX** – a dedicated multi-widget React experience with detailable cards, log viewer, mini command console, and Papermill job monitor. This ships as a second Vite entry (`control-center.html`).
4. **Notebook parity** – a new `control_center_relay.ipynb` notebook mirrors the widgets by querying the same API. Papermill smoke tests execute all three notebooks in CI.
5. **Storybook + Vitest coverage** – every widget has a Storybook story and lightweight test so the Relay experience stays regression-proof.
6. **Automation** – GitHub Actions workflow already named "Full Test Suite" now orchestrates backend pytest, Papermill notebooks, frontend lint/test/build, Storybook build, and the new relay tests.

---

## 2. Service Layout

```
┌──────────────────────────┐      REST/SSE       ┌──────────────────┐
│  Relay UI (Vite)   │ ◀─────────────────▶ │ FastAPI Control   │
│  • Control widgets      │                    │  Router           │
│  • Notebook monitor     │   (Ops Deck shares │  • /api/control/* │
│  • Command console      │    the REST APIs)  │  • Orchestrator   │
└──────────────────────────┘                    └──────────────────┘
            ▲                                              │
            │                   snapshots/logs             │
            │                                              ▼
┌──────────────────────────┐                    ┌──────────────────┐
│ Lab Orchestrator        │                    │ Papermill Runner │
│ • scripts/labctl.sh     │◀──── CLI ───────▶  │ • Notebook jobs  │
│ • LabControl.psm1       │                    │ • RU checks      │
└──────────────────────────┘                    └──────────────────┘
```

### Responsibilities

| Component | Responsibilities | Notes |
|-----------|------------------|-------|
| `app/api/control.py` | Aggregate orchestrator snapshot, stream `.labctl` logs, trigger papermill runs, store widget presets. | Uses `asyncio.create_task` to run notebooks without blocking responses.
| `scripts/control_center.py` | CLI for `start-services`, `stop-services`, `status`, `storybook`, `papermill`, and `relay` preview. | Wraps `LabOrchestrator` + npm scripts.
| Relay Vite entry | Renders `ControlCenterApp`, polls `/api/control/status`, `/api/control/logs`, `/api/control/notebooks`, and provides command palette. | Lives beside existing Ops Deck UI but builds into a separate bundle.
| New notebook | Queries `/api/control/status`, enriches with SQLite insights, renders Plotly timeline & RU chart. | Stored at `workshop/notebooks/control_center_relay.ipynb`.

---

## 3. API Contract

### 3.1 `/api/control/status`
- **GET** returns `{ services: [...], processes: [...], logs: {...}, timestamp }` filtered for widget consumption.
- **Query params**: `include_logs=bool` (default `false`), `limit=int` for log lines.

### 3.2 `/api/control/logs`
- **GET** returns `{ service: str, lines: [str] }` for a single service.
- Valid `service`: `backend`, `frontend`, `workshop`, `relay`.

### 3.3 `/api/control/notebooks`
- **GET** lists previous Papermill jobs (cached in-memory).
- **POST** body `{"name": "control_center_relay", "parameters": {...}}` kicks off an async Papermill execution under `workshop/notebooks/_papermill/<name>-<stamp>.ipynb`.

### 3.4 `/api/control/widgets`
- **GET** returns curated sample data (LLM latency sparkline, RU budgets, synthetic keystroke totals) used by placeholder widgets.

---

## 4. Relay Widgets

| Widget | Data Source | Interaction |
|--------|-------------|-------------|
| ServiceGrid | `/api/control/status` | Poll every 5s, show runtime + uptime, CTA to open logs.
| NotebookMonitor | `/api/control/notebooks` | Shows running/completed Papermill jobs, allows triggering rerun.
| CommandConsole | `/api/control/logs` + `/api/control/status` | Users send start/stop/log commands; output rendered inline.
| MetricsTicker | `/api/control/widgets` | Animated counters for LLM latency, RU burn, keystroke volume.
| TailLogViewer | `/api/control/logs?service=backend` | Streams latest 120 lines, auto-scroll.
| ReleaseLogPanel | `/api/release-log` | Lists the newest `data/logs/release.log` entries (release pipeline + harness) with inline timeline badges and manual refresh. |

Each widget is an independent React component with a dedicated Storybook story and test. A tiny context provider (`ControlCenterProvider`) caches shared data + toggles theme (light/dark) for embed.

---

## 5. Notebook Integration

- Notebook stored in git with lightweight cells (SQLite queries + HTTP requests).
- Papermill parameters: `DB_PATH`, `CONTROL_STATUS_URL`, `OUTPUT_DIR`.
- Execution uses repo virtualenv (Papermill already installed via `workshop/requirements.txt`).
- Tests: `tests/test_notebooks.py` param list now includes the new notebook. Jobs run in CI as part of the Full Test Suite.

---

## 6. Automation & CI

1. `scripts/control_center.py start` boots backend + both Vite entrypoints via the Lab Orchestrator and writes consolidated status JSON to `.labctl/state/aggregate.json`.
2. `scripts/control_center.py relay` proxies to `npm run relay:dev`, keeping the widget UI in sync with backend data.
3. GitHub workflow adds three steps:
   - `npm run test:relay` (Vitest suite for new widgets).
   - `npm run storybook:relay` (control-only Storybook build reused for Chromatic/visual regressions).
   - `npm run chromatic` (rebuilds the relay Storybook subset and uploads to Chromatic; requires `CHROMATIC_PROJECT_TOKEN`).
4. Workflow artifact uploads executed notebooks from `_papermill/` for traceability.

---

## 7. Deliverables Checklist

- [x] `docs/CONTROL_CENTER_RELAY.md` (this file).
- [x] Backend control router + schemas/tests.
- [x] `scripts/control_center.py` orchestrator CLI.
- [x] Relay Vite entry + widgets + tests + stories.
- [x] `control_center_relay.ipynb` + Papermill test update.
- [x] CI workflow updates + launch instructions in README.

Once all boxes are checked, the repo ships with a fully automated control center that spans backend, frontend, notebooks, and tooling.

---

## 8. Elements Canvas Preview

- The Control Center now embeds the **Elements** workbench—a drag-and-drop node scaffold powered by a shared registry and Zustand store located in `src/elements/`.
- The preview lets you explore the prompt → LLM → notebook preset, tweak parameters, and connect additional nodes before the backend executor lands.
- Storybook ships the same canvas under `Elements/Workbench`, and the full architecture/spec is tracked in `docs/ELEMENTS_SPEC.md` so backend + notebook engineers can implement their halves without deviating from the contract.
