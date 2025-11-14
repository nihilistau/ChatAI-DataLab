# ChatAI + DataLab — Project Overview

This document captures the end-to-end plan for the ChatAI data-capture experience and the DataLab insight environment. It is written for a solo developer who wants a pragmatic, GitHub-first workflow that can be reproduced on any VS Code instance—local or remote.

---

## 1. Vision & Objectives

- **Reliable data capture**: Instrument every user prompt to record raw text, cadence, pauses, and edit history without slowing the UI.
- **Unified storage**: Persist structured conversations plus metadata in a portable SQLite database that can later be upgraded to Postgres or Cosmos DB.
- **Fast analysis loops**: Provide Jupyter-ready tooling so insights, visualizations, and experiments stay close to the source data.
- **Portable ops story**: Everything must run from a monorepo with predictable setup instructions (scripted and containerized) that work on cloud VMs, local laptops, and Codespaces.

## 2. High-Level Architecture

```
┌────────────┐    HTTPS    ┌───────────────┐        ┌────────────────┐
│  ChatAI UI │ ─────────▶ │ FastAPI Relay │ ─────▶ │ interactions.db │
└────────────┘            └───────────────┘        └────────────────┘
		  ▲                         │                         │
		  │      LLM APIs / Ollama  ▼                         │
		  │──────────────────────▶ External Model             │
		  │                                                  ▼
		  │                                           ┌────────────┐
		  └────────────────────────────────────────── │  DataLab   │
																	 └────────────┘
```

| Layer      | Responsibilities | Key Tech |
|------------|------------------|----------|
| ChatAI UI  | Capture prompt text + metadata, display AI responses | SvelteKit or React (Vite) |
| FastAPI    | Validate payloads, call LLM, persist data, expose REST APIs | FastAPI, Pydantic, SQLAlchemy |
| Storage    | Durable interaction history, structured metadata, reproducible file-based DB | SQLite (later Postgres/Cosmos DB) |
| DataLab    | Notebook-driven exploration, scripts, dashboards | JupyterLab, pandas, Plotly |

## 3. Repository Layout

```
ChatAI-DataLab/
├── chatai/
│   ├── frontend/        # SvelteKit/React instrumentation client
│   ├── backend/         # FastAPI service, SQLAlchemy models
│   └── Dockerfile       # Builds combined API image (serves static assets via ASGI)
├── datalab/
│   ├── notebooks/       # Exploratory and production notebooks
│   ├── scripts/         # Reusable analysis helpers & CLI utilities
│   └── requirements.txt # Data science dependencies
├── data/
│   └── interactions.db  # SQLite database (mounted volume in Docker)
├── scripts/
│   ├── setup.sh         # Idempotent environment bootstrap
│   └── fetch_assets.sh  # Optional large-model / dataset download hooks
├── docker-compose.yml   # Local Orchestration: API + frontend + DataLab
└── PROJECT_OVERVIEW.md  # You are here
```

## 4. ChatAI — Data Acquisition Stack

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

- Start with SQLite under `data/interactions.db` for zero-config; ensure the file lives on a mounted volume so Docker, local dev, and remote VMs share the same data.
- Keep items < 2 MB to ensure easy migration to Cosmos DB or PostgreSQL later; store large assets (audio, images) by reference (blob URLs, Drive links).
- Future-proof with partition-friendly identifiers (e.g., `tenantId:userId:sessionId`).

## 5. DataLab — Insight Workspace

### 5.1 Environment & Dependencies

List to pin in `datalab/requirements.txt`:

| Purpose | Packages |
|---------|----------|
| Notebook runtime | `jupyterlab`, `ipykernel`, `python-dotenv` |
| Data wrangling | `pandas`, `numpy`, `polars` (optional) |
| Visualization | `matplotlib`, `seaborn`, `plotly`, `altair` |
| NLP | `spacy`, `nltk`, `textstat` |
| Modeling | `scikit-learn`, `umap-learn` |

### 5.2 Typical Workflow

1. **Launch**: `cd datalab && source venv/bin/activate && jupyter lab` (or run the Docker service).
2. **Connect to data**:
	```python
	import sqlite3, json
	import pandas as pd

	conn = sqlite3.connect("../data/interactions.db")
	df = pd.read_sql_query("SELECT * FROM interactions", conn)
	meta = df["typing_metadata_json"].apply(json.loads)
	```
3. **Feature engineering**: explode keystrokes/pause arrays, compute WPM, hesitation counts, etc.
4. **Visualization**: build static charts (Matplotlib/Seaborn) or interactive dashboards (Plotly) showing pause heatmaps, average typing speed vs. response quality, etc.
5. **Packaging insights**: store reusable helpers inside `datalab/scripts/` (e.g., `metrics.py`, `visuals.py`) and import them into notebooks to stay DRY.

## 6. Deployment & Automation

### 6.1 `scripts/setup.sh`

The installer is now distro-aware and idempotent:

- Detects `apt` (Debian/Ubuntu) or `pacman` (Arch) and installs Python 3, Node.js, npm, and Git. If neither is present it prints manual instructions.
- Creates isolated `.venv` folders inside `chatai/backend` and `datalab`, upgrades `pip`, installs pinned requirements, and builds the frontend bundle.
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

- Manages `backend`, `frontend`, and `datalab` jobs via PID files under `.labctl/state` and streams logs from `.labctl/logs`.
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
| `chatai` | `./chatai` | Builds FastAPI backend, serves compiled frontend via `uvicorn` + `StaticFiles` |
| `web` | `nginx:alpine` (optional) | CDN-like caching + TLS termination for the SPA |
| `datalab` | `jupyter/minimal-notebook` or custom image | Starts JupyterLab with repo mounted | 
| `db` | `sqlite` volume | Bind-mount `data/` for durability |

All services share the `./data` volume for `interactions.db`, ensuring the DataLab reflects newly ingested conversations instantly.

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
| `Start-LabJob -Name datalab` | Boot Jupyter Lab in no-browser mode. |
| `Start-AllLabJobs` / `Stop-AllLabJobs -Force` | Meta controls to bring the full stack up/down. |
| `Restart-LabJob -Name frontend` / `Restart-AllLabJobs` | Convenience resets for flaky dev servers. |
| `Show-LabJobs` / `Receive-LabJobOutput -Name backend` | Inspect job states and stream buffered logs. |
| `Remove-LabJob -Name tail` | Forcefully stop and remove any lab job. |
| `Save-LabWorkspace` / `Restore-LabWorkspace -ArchivePath <zip>` | Snapshot or restore repo + data into timestamped archives under `backups/`. |
| `Install-LabDependencies -Target backend|frontend|datalab|all` | Reinstall per-project dependencies (creates `.venv` envs + runs `npm install`). |
| `New-LabPackage` | Builds the frontend, runs backend pytest, and emits a release zip (also under `backups/`). |

`Invoke-LabControlCenter` renders an at-a-glance dashboard showing job status plus the most useful commands so you can treat the PowerShell terminal like a mini operations console from inside VS Code. When you need to interact with Linux copies of the project from Windows, run `Invoke-LabUnixControl status` (optionally `-Distribution Ubuntu-22.04`) to proxy any Bash command through WSL, or call `Invoke-LabUnixControl start-all` to spin up the entire stack without leaving PowerShell.

## 7. Operational Notes & Roadmap

1. **Security & secrets**: store API keys in `.env` files loaded by FastAPI and never check them into GitHub. For multi-tenant deployments consider Azure Key Vault or AWS Secrets Manager.
2. **Testing**: add component tests for the input recorder, FastAPI payload validation, and SQLAlchemy persistence. Provide smoke notebooks verifying schema assumptions.
3. **Observability**: enable structured logging (JSON) and capture Cosmos DB / LLM diagnostics for latency analysis.
4. **Future enhancements**:
	- Add WebSocket streaming for real-time AI responses.
	- Promote SQLite to a managed database when RU/s or size exceeds limits.
	- Create a reusable Python package inside `datalab/` for metrics so notebooks stay lightweight.
	- Ship templated Jupyter notebooks (e.g., "interaction summary", "pause heatmap", "prompt rewrite tree").

With this plan in place, you can confidently spin up the repo on any machine, capture rich prompt telemetry, and immediately explore it in DataLab without context switching.