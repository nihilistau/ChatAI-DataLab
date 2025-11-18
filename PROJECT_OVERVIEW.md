# ChatAI + Playground — Project Overview

> **Milestone:** Framework v1.0.0 (Complete)  
> **Snapshot:** 2025-11-15 14:00 UTC  
> **Status:** Fully working capture + analysis framework. New additions are logged in `docs/GOALS_AND_ACHIEVEMENTS.md` and mirrored in the “Expanded Functionality” table below.

<!-- Snapshot recorded: 2025-11-15T14:00:00Z -->

This document captures the completed ChatAI capture pipeline and Kitchen-powered Playground environment. Treat it as the authoritative description of what exists today—structure, commands, and feature set. Future enhancements must be documented as dated entries before they graduate into this file.

## Expanded Functionality

| Date (UTC) | Feature | Components | Notes |
| --- | --- | --- | --- |
| 2025-11-15 | Repo-wide PowerShell Search Toolkit | `scripts/powershell/SearchToolkit.psm1`, `scripts/powershell/search-presets.json`, `scripts/powershell/examples/find-todos.ps1` | Adds reusable presets, JSONL logging, and dry-run stats for observability-ready code sweeps. |
| 2025-11-15 | LabControl Search Proxy | `scripts/powershell/LabControl.psm1`, `scripts/lab-control.ps1` | LabControl can now run any preset via `-SearchPreset` / `-SearchPattern`, keeping Windows + Linux ops flows aligned. |
| 2025-11-15 | Release Automation Helper | `scripts/powershell/LabControl.psm1`, `scripts/lab-control.ps1`, `docs/RELEASE_CHECKLIST.md` | `Publish-LabRelease` runs integrity, tagging, and optional pushes (with `-DryRun` support) so Framework releases stay reproducible. |
| 2025-11-15 | Release Checklist Runner | `scripts/release_checklist.ps1`, `scripts/powershell/LabControl.psm1` | `-RunTests` flag executes backend/notebook/frontend checks before tagging; `-FinalizeChangelog` and `-UpdateIntegrity` keep metadata fresh. |
| 2025-11-15 | Search telemetry ingestion | `scripts/search_telemetry.py`, `kitchen/telemetry/search_ledger.py`, `kitchen/notebooks/search_telemetry.ipynb`, `tests/test_notebooks.py`, `scripts/lab-control.ps1` | Search Toolkit logs hydrate into `data/search_telemetry.json`, powering notebooks + Ops Deck charts (ingest via LabControl or direct CLI). |
| 2025-11-15 | Release pipeline presets | `scripts/powershell/LabControl.psm1`, `scripts/lab-control.ps1`, `docs/CHANGELOG_TEMPLATE.md` | `Publish-LabRelease` now supports `-Bump` version presets, changelog templating, and the `-ReleasePipeline` job to run tests, integrity, and pushes end-to-end. |
| 2025-11-15 | Command history filters | `playground/backend/app/api/commands.py`, `tests/test_commands_api.py` | `/api/commands` now supports `status`, `tag`, and `limit` filters plus a dedicated `/api/commands/{id}/history` endpoint for paginated history access. |
| 2025-11-15 | Lab bootstrap + command listing | `scripts/lab-bootstrap.ps1`, `scripts/powershell/LabControl.psm1`, `configs/lab_environment_config.md` | Bootstraps env vars, deep scans notebooks/backend/frontend, exposes `List-Commands` inside LabControl, and documents canonical syntax/paths. |
| 2025-11-15 | Diagnostics + healthcheck wiring | `kitchen/lab_paths.py`, `kitchen/diagnostics.py`, `scripts/control_health.py`, `playground/frontend/src/lib/api.ts`, `scripts/powershell/LabControl.psm1` | Unified `LAB_ROOT` helpers, structured diagnostics log, Papermill metadata, Control Center fixture toggles, and the `Test-LabHealth` command. |

---
## Overview ##


## 1. Libraries Purpose

**Reliable data capture**: Instrument every user prompt to record raw text, cadence, pauses, and edit history without slowing the UI.
**Unified storage**: Persist structured conversations plus metadata in SQLite or Cosmos DB (runtime selectable). Migration and schema upgrades are supported as future enhancements.
**Kitchen-first experimentation**: Provide notebook tooling (Recipes + Cookbooks) so Playground layouts, workflows, and analyses stay close to the source data.
**Portable ops story**: Everything must run from a monorepo with predictable setup instructions (scripted and containerized) that work on cloud VMs, local laptops, and Codespaces.

## 2. High-Level Architecture

```
┌────────────┐    HTTPS    ┌───────────────┐        ┌────────────────────────────────┐
│ Frontend   │ ─────────▶ │ FastAPI Relay │ ─────▶ │ Playground Data Store (pluggable) │
└────────────┘            └───────────────┘        └────────────────────────────────┘
	  ▲                         │                         │
	  │      LLM APIs / Ollama  ▼                         │
	  │──────────────────────▶ External Model             │
	  │                                                  ▼
	  │                                           ┌────────────┐
	  └───────────────────── Kitchen Recipes ───▶ │  Kitchen   │
				 └────────────┘
```

| Layer      | Responsibilities | Key Tech |
|------------|------------------|----------|
| Frontend (Control Surface) | Capture prompt text + metadata, display AI responses, render layouts authored by the Kitchen | SvelteKit or React (Vite) |
| FastAPI (Orchestrator)   | Validate payloads, call LLM, persist data, expose REST APIs, stream manifest updates | FastAPI, Pydantic, SQLAlchemy |
| Storage    | Durable interaction history, structured metadata, reproducible provider-agnostic store | SQLite (default), JSON snapshot, Cosmos DB |
| Kitchen    | Notebook-driven system design (Recipes), scripts, dashboards, workflow automation | JupyterLab, pandas, Plotly |

### 2.1 Playgrounds & Tenancy

- A **Playground** is a deployable combination of the three layers above plus configuration that scopes them to a purpose or tenant.
- Playgrounds are versioned via Cookbooks authored in the Kitchen; the backend promotes those manifests and the frontend reflects them live.
- Tenants own one or more Playgrounds. Namespaces follow `<tenant>/<playground>/<revision>` and map to storage rows plus manifest history.
- Refer to `docs/PLAYGROUND_GUIDE.md` for deeper definitions, vocabulary, and the Welcome Cookbook plan.

## 3. Repository Layout

```
ChatAI-DataLab/
├── playground/
│   ├── frontend/        # SvelteKit/React instrumentation client
│   ├── backend/         # FastAPI service, SQLAlchemy models
│   └── Dockerfile       # Builds combined API image (serves static assets via ASGI)
├── kitchen/
│   ├── notebooks/       # Recipes + Cookbooks that define Playgrounds
│   ├── scripts/         # Layout/manifest helpers & CLI utilities
│   └── requirements.txt # Notebook + widget dependencies
├── legacy/
│   └── datalab/         # Archived notebooks/scripts kept for historical reference
├── data/
│   ├── interactions.db        # Auto-generated when DATABASE_PROVIDER=sqlite (managed via scripts/playground_store.py)
│   └── playground_store.json  # Auto-generated when DATABASE_PROVIDER=json (same CLI emits/reads this snapshot)
├── scripts/
│   ├── setup.sh         # Idempotent environment bootstrap
│   └── fetch_assets.sh  # Optional large-model / dataset download hooks
├── docker-compose.yml   # Local Orchestration: API + frontend + Kitchen
└── PROJECT_OVERVIEW.md  # You are here
```

## 4. ChatAI — Data Acquisition Stack

### Status snapshot (Framework v1.0.0 · Nov 2025)

- ✅ **Frontend instrumentation shipped** — `playground/frontend/src/components/PromptRecorder.tsx` records keystrokes, pauses, snapshots, and submits a single `/api/chat` payload with optimistic UI updates.
- ✅ **FastAPI storage + relay live** — `POST /api/chat` in `playground/backend/app/api/routes.py` persists interactions via the SQLAlchemy models in `app/models.py`, captures metadata/LLM output, and returns latency stats.
- ✅ **Repo hygiene enforced** — Automated sweeps via the Search Toolkit confirm no first-party `TODO` or "unimplemented" markers remain; any new TODOs require justification + ticket references.

### 4.1 Frontend Instrumentation

- **Framework**: SvelteKit (preferred) or React + Vite for quick SSR, routing, and TypeScript support.
- **State model**: Keep the current prompt plus an in-memory event buffer; flush to the backend on submit.
- **Captured Signals**
  - _Keystroke events_: `{ key, code, timestamp }` on every `keydown` (millisecond precision).
  - _Pause events_: Debounced observer triggers when typing idle ≥ 700 ms, storing `{ start, durationMs }`.
  - _Snapshots_: Interval timer (≈1.5 s) or pause trigger records `{ timestamp, text }` for edit reconstruction.
  - _Submission summary_: `finalPromptText`, `tokenEstimate`, `totalDurationMs`, derived typing speed stats.
- **Transport**: Single POST `/api/chat` with the prompt, metadata arrays, UI version, and optional session ID.
- **UX**: Optimistic display of AI response; fallback toast if backend returns errors or 429s.

### 4.2 FastAPI Relay

- **Entry point**: `POST /api/chat` receives `ChatPayload` (Pydantic model) and returns `ChatResponse`.
- **Pipeline**
  1. Validate payload & enrich with server timestamps/IP hash.
  2. Call adapter that targets OpenAI, Anthropic, or a local Ollama endpoint (pluggable via strategy pattern).
  3. Persist into SQLite using SQLAlchemy ORM with the following table:

	  | Column | Type | Notes |
	  |--------|------|-------|
	  | `id` | UUID | Primary key |
	  | `user_prompt_text` | TEXT | Final text from UI |
	  | `typing_metadata_json` | JSON | Raw structure from frontend |
	  | `ai_response_text` | TEXT | Model answer |
	  | `model_name` | TEXT | e.g., `gpt-4o-mini` |
	  | `created_at` | DATETIME | Server timestamp |

  4. Return `{ responseText, interactionId, latencyMs }` to the UI.
- **Best practices**: Reuse a singleton `CosmosClient`/LLM client, honor retry-after headers, log diagnostic strings when latency spikes, and surface 429 backoff hints to the UI.

### 4.3 Database Considerations

- The Playground selects a provider via `DATABASE_PROVIDER` (`sqlite`, `json`, or `cosmos`). Run `python scripts/playground_store.py summary` to confirm the active backend, or `python scripts/playground_store.py interactions --json` to dump recent rows without hand-writing SQL.
- File-backed runs default `DATABASE_PATH` to `data/interactions.db`, but treat it as an implementation detail surfaced through env vars or `python scripts/playground_store.py ...`. Only mount/share that path when you intentionally opt into SQLite; JSON/Cosmos providers ignore the file and automatically hydrate their own backing store.
- Keep items < 2 MB to ensure easy migration to Cosmos DB or PostgreSQL later; store large assets (audio, images) by reference (blob URLs, Drive links).
- Future-proof with partition-friendly identifiers (e.g., `tenantId:userId:sessionId`).

## 5. Kitchen — Notebook Workspace

The Kitchen fully replaces the old DataLab helpers. New Recipes and Cookbooks live under `kitchen/`, while frozen notebooks reside under `legacy/datalab/` for historical reference. Treat `kitchen/` as the sole source of truth for new work; the legacy archive is read-only.

### 5.1 Environment & Dependencies

List to pin in `kitchen/requirements.txt` (superset of the former DataLab requirements):

| Purpose | Packages |
|---------|----------|
| Notebook runtime | `jupyterlab`, `ipykernel`, `python-dotenv` |
| Data wrangling | `pandas`, `numpy`, `polars` (optional) |
| Visualization | `matplotlib`, `seaborn`, `plotly`, `altair` |
| NLP | `spacy`, `nltk`, `textstat` |
| Modeling | `scikit-learn`, `umap-learn` |

### 5.2 Recipe authoring workflow

1. **Launch**: `cd kitchen && source venv/bin/activate && jupyter lab` (or run the Docker service). Only open `legacy/datalab/notebooks/` when inspecting archived runs.
2. **Connect to data**:
	```
	import json
	from kitchen.scripts.metrics import load_interactions

	df = load_interactions(limit=500)  # honors DATABASE_PROVIDER (sqlite/json/cosmos)
	meta = df["typing_metadata_json"].apply(json.loads)
	```
3. **Define layouts and logic**: declare widget trees, bind them to backend endpoints, and emit manifest snapshots from within the Recipe.
4. **Visualization**: build static charts (Matplotlib/Seaborn) or interactive dashboards (Plotly) showing pause heatmaps, average typing speed vs. response quality, etc.
5. **Packaging & publishing**: store reusable helpers inside `kitchen/scripts/` and export Cookbooks that the backend can promote into Playgrounds.

### 5.3 Cookbooks, Recipes & Elements

- `kitchen/scripts/elements.py` centralizes sample graph presets plus helpers for summarizing, validating, and simulating Elements DAGs in pure Python.
- Papermill-friendly notebooks such as `kitchen/notebooks/welcome_cookbook.ipynb` (new) and the archived `legacy/datalab` copies (`elements_playground.ipynb`, `elements_reporting.ipynb`) demonstrate graph inspection, dry-run execution, and report generation that mirrors the backend `/api/elements` service.
- Cookbooks accept overrides/graph IDs via Papermill parameters, keeping the Control Center UI, backend API, and Kitchen workflows aligned.
- The Welcome Cookbook ships five Recipes (Orientation, Getting Started, Tutorial Build, Sample Playground, Advanced Integrations) and autoloads for new Kitchen sessions.

### 5.4 Manifest publishing workflow

- The backend now exposes `/api/playgrounds/{tenant}/{playground}/manifests` for Kitchen-driven publishing. Each POST stores an immutable row inside the `playground_manifests` table (tenant, playground, revision, checksum, cookbook/recipe metadata).
- Companion GET routes (`/manifests`, `/manifests/latest`, `/manifests/{revision}`) let the Control Surface and deployment tooling diff or roll back manifests without scraping notebooks.
- Kitchen notebooks import `kitchen/scripts/manifest.py` and use `ManifestPublisher`, which respects `PLAYGROUND_API_URL` (default `http://localhost:8000/api`) and optional `KITCHEN_AUTHOR` env vars for attribution.
- The Welcome Cookbook now calls `publish_manifest_snapshot(...)`, so Recipe 1 publishes a preview and Recipe 3 promotes the tutorial manifest via the real API rather than the old print-only mock.
- Revisions auto-increment per namespace. Provide an optional `revision_label` (e.g., `v0`, `alpha`) to preserve notebook semantics while checksums guarantee diffable audit trails.

## 6. Deployment & Automation

### 6.1 `scripts/setup.sh`

The installer is now distro-aware and idempotent:

- Detects `apt` (Debian/Ubuntu) or `pacman` (Arch) and installs Python 3, Node.js, npm, and Git. If neither is present it prints manual instructions.
- Creates isolated `.venv` folders inside `playground/backend` and `kitchen`, upgrades `pip`, installs pinned requirements, and builds the frontend bundle.
- Calls `scripts/fetch_assets.sh` only when it exists/executable, so clean clones don’t fail if large-asset automation hasn’t been defined yet.
- Prints the exact commands to start each service once provisioning finishes.

Usage:

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Run this script immediately after cloning on any Debian, Ubuntu, or Arch-based VM (it also works inside Codespaces or WSL). Re-running is safe; it will simply refresh dependencies and rebuild artifacts.

### 6.2 Linux & Remote Lab Control (`scripts/labctl.sh`)

Linux hosts (bare metal, VPS, Codespaces, WSL, or containers) get a Bash-native orchestration utility that mirrors the Windows PowerShell experience.

Key features:

- Manages `backend`, `frontend`, and `kitchen` jobs via PID files under `.labctl/state` and streams logs from `.labctl/logs`.
- Supports `start`, `stop`, `restart`, `status`, `logs`, and meta commands (`start-all`, `stop-all`).
- Provides `backup`/`restore` using `tar` archives plus `install` to rerun `scripts/setup.sh`.
- Includes `remote` subcommand that tunnels any action over SSH, e.g. `./scripts/labctl.sh remote ubuntu@edge ./opt/ChatAI-DataLab start-all`.

Every command is a subcommand, making it easy to script:

```bash
./scripts/labctl.sh status
./scripts/labctl.sh start backend
./scripts/labctl.sh start-all
./scripts/labctl.sh backup ~/backups/lab-$(date +%F).tar.gz
./scripts/labctl.sh remote user@host /srv/ChatAI-DataLab stop-all
```

On Windows you can bridge into the Linux workflow with WSL or Git Bash using `Invoke-LabUnixControl` (see §6.4) or by running `wsl ./scripts/labctl.sh status` directly.

### 6.3 Docker Compose (next iteration)

| Service | Image/Context | Purpose |
|---------|---------------|---------|
| `playground-api` | `./playground/backend` (multi-stage image defined in the new `playground/Dockerfile` tree) | FastAPI service plus background workers; exposes `/api/*` and health probes. |
| `playground-frontend` | `./playground/frontend` (same Dockerfile tree as above, different target) | Serves the compiled Control Center SPA through Vite’s preview server or an nginx stage. |
| `kitchen` | `./kitchen` (extends `jupyter/minimal-notebook`) | Launches JupyterLab with Kitchen notebooks + Papermill helpers pre-installed. |
| `db` | Named volume mounted at `/data` | Persists `data/interactions.db`, telemetry ledgers, and manifest exports so all containers see the same state. |

> _Status_: the compose file is being rebuilt around the `playground/*` layout. Until it lands, treat this table as the target topology for the next iteration and continue running services via `labctl` / LabControl.

All services share the `./data` volume whenever the SQLite provider is active, ensuring the Kitchen notebooks reflect newly ingested conversations instantly. JSON/Cosmos providers skip the filesystem coupling but still hydrate Kitchen notebooks through the shared data store helpers.

### 6.4 PowerShell Control Center

Windows + VS Code users now get a modular terminal orchestration layer located in `scripts/powershell/LabControl.psm1` (auto-loaded via `scripts/lab-control.ps1`). Import it once per PowerShell session:

```
pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -ControlCenter
```

Or manually:

```powershell
Import-Module .\scripts\powershell\LabControl.psm1
Invoke-LabControlCenter
```

Key commands (each proxies to standard `Start-Job` / `Stop-Job` primitives but manages paths, env vars, and status aggregation):

| Command | Description |
|---------|-------------|
| `Start-LabJob -Name backend` | Launch FastAPI (`uvicorn`) as a background job with proper `PYTHONPATH`. |
| `Start-LabJob -Name frontend` | Run the Vite dev server (`npm run dev -- --host`). |
| `Start-LabJob -Name kitchen` | Boot Jupyter Lab in no-browser mode. |
| `Start-AllLabJobs` / `Stop-AllLabJobs -Force` | Meta controls to bring the full stack up/down. |
| `Restart-LabJob -Name frontend` / `Restart-AllLabJobs` | Convenience resets for flaky dev servers. |
| `Show-LabJobs` / `Receive-LabJobOutput -Name backend` | Inspect job states and stream buffered logs. |
| `Remove-LabJob -Name tail` | Forcefully stop and remove any lab job. |
| `Save-LabWorkspace` / `Restore-LabWorkspace -ArchivePath <zip>` | Snapshot or restore repo + data into timestamped archives under `backups/`. |
| `Install-LabDependencies -Target backend|frontend|kitchen|all` | Reinstall per-project dependencies (creates `.venv` envs + runs `npm install`). |
| `New-LabPackage` | Builds the frontend, runs backend pytest, and emits a release zip (also under `backups/`). |

`Invoke-LabControlCenter` renders an at-a-glance dashboard showing job status plus the most useful commands so you can treat the PowerShell terminal like a mini operations console from inside VS Code. When you need to interact with Linux copies of the project from Windows, run `Invoke-LabUnixControl status` (optionally `-Distribution Ubuntu-22.04`) to proxy any Bash command through WSL, or call `Invoke-LabUnixControl start-all` to spin up the entire stack without leaving PowerShell.

## 7. Operational Practices & Change Tracking

1. **Secrets management**: Store API keys in repo-local `.env` files that FastAPI and notebooks consume via `python-dotenv`. Never commit secrets; production deployments should source them from managed vaults (Azure Key Vault, AWS Secrets Manager, etc.).
2. **Test + notebook parity**: `playground/backend/tests` and `kitchen/tests` provide regression coverage for the recorder payload, FastAPI schema validation, metrics helpers, and Papermill notebooks. Extend these suites before modifying public endpoints or notebook contracts.
3. **Observability hooks**: Structured logging, the Search Toolkit presets, and the new `data/search_telemetry.json` ledger (hydrated from `logs/search-history.jsonl`) form the baseline telemetry story. Run `Update-LabSearchTelemetry` (or the LabControl `-RunSearchTelemetryIngestion` flag) plus `Get-SearchHistory` before every milestone cut so Ops Deck widgets can trend hygiene sweeps.
4. **Change documentation**: Every shipped addition must (a) add a dated entry to the “Expanded Functionality” table above, (b) append a record to `docs/GOALS_AND_ACHIEVEMENTS.md`, and (c) update relevant tags/configs. Ideas that are not yet implemented stay out of this file.

With the framework baseline locked, this overview now functions as the source of truth for what is production-ready. Treat any future edits as release notes for implemented work only.