# ChatAI · DataLab

Instrument every keystroke inside ChatAI, relay it through FastAPI, and explore the signal-rich corpus in DataLab. This mono-repo now ships with opinionated documentation, tagging standards, and an integrity toolchain so you can bootstrap, audit, and evolve the stack with confidence.

## Why this project exists

- **Full-fidelity capture** – pause telemetry, edit history, and prompt context stay linked to each inference.
- **Insight loop** – DataLab notebooks and scripts stay in-repo, keeping EDA reproducible.
- **Operational parity** – PowerShell + Bash control planes and Ops Deck widgets expose the same services/logs.
- **Governed change** – Hash-based integrity snapshots, checkpoints, and repair flows guard the codebase.

## Feature highlights

| Area | Highlights |
| --- | --- |
| Frontend (`chatai/frontend`) | React + Vite command center with Prompt Recorder, Ops Deck, Tail log, Artifact shelf, dynamic themes |
| Backend (`chatai/backend`) | FastAPI relay, SQLAlchemy models, pluggable LLM client, artifact + tail-log APIs |
| Control plane (`controlplane/`) | Cross-platform orchestrator that powers the Ops Deck and CLI utilities |
| DataLab (`datalab/`) | Ready-to-run notebooks (see `hypothesis_control.ipynb`), metrics scripts, pinned requirements |
| Tooling | `scripts/setup.sh`, PowerShell `LabControl`, `labctl.sh`, and the new `project_integrity.py` guards |

## Repository map

```
chatai/         # frontend + backend source
controlplane/   # ops/orchestration helpers
scripts/        # installers + job control
scripts/powershell/  # Windows control center
scripts/project_integrity.py  # hash + checkpoint CLI
configs/        # manifests, tagging + guardrail config
backups/        # integrity snapshots land here
.datalab/       # notebooks + analysis assets
```

See `docs/FILE_SYSTEM.md` for the authoritative outline, guardrails, and naming conventions.

## Quick start

1. **Clone & install** (Linux/macOS/WSL):
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```
2. **Windows control center**:
   ```powershell
   pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -ControlCenter
   ```
3. **DataLab**:
   ```bash
   cd datalab
   source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
   jupyter lab --notebook-dir=notebooks
   ```
4. **Integrity baseline**:
   ```bash
   python scripts/project_integrity.py init --reason "initial clone"
   ```

## Working in the stack

- **Frontend dev server**: `cd chatai/frontend && npm install && npm run dev -- --host` (or use LabControl jobs).
- **Backend API**: `cd chatai/backend && .venv/Scripts/uvicorn app.main:app --reload`.
- **Ops Deck**: automatically polls `/api/ops/status` and surfaces controlplane actions. Tail logs funnel to both UI and DataLab notebook (#ops tag).
- **Control Center Playground**: `npm run playground:dev` inside `chatai/frontend` (or `python scripts/control_center.py playground`) to launch the multi-widget control UI backed by `/api/control/*` endpoints.
- **Control Center CLI**: `python scripts/control_center.py start|stop|status|notebook` controls Lab Orchestrator services, opens the Playground, or executes the new Papermill notebook without leaving the terminal.
- **Hypothesis Workflow Control Lab notebook**: open `datalab/notebooks/hypothesis_control.ipynb` for experiment design, voting, telemetry charts, and ops log streaming.

## Documentation suite

| Doc | Purpose |
| --- | --- |
| `docs/INSTALL.md` | OS-specific setup, verification, and troubleshooting |
| `docs/TUTORIALS.md` | Guided workflows for instrumentation → Ops Deck → DataLab insights |
| `docs/FILE_SYSTEM.md` | Official file tree, guardrails, naming and ownership rules |
| `docs/INTEGRITY.md` | Hash + checkpoint workflow, repair steps, metadata schema |
| `docs/TAGS.md` | Shared tagging standard for code comments, Ops Deck, and DataLab |

## Integrity + versioning guardrails

`scripts/project_integrity.py` keeps a manifest of every tracked file (hash, size, tags, timestamps) under `.project_integrity/index.json`. Core commands:

```
python scripts/project_integrity.py init --reason "Initial baseline"
python scripts/project_integrity.py status                     # diff vs. manifest
python scripts/project_integrity.py checkpoint --tag release --reason "0.2.0"
python scripts/project_integrity.py verify chatai/backend/app/models.py
python scripts/project_integrity.py repair chatai/backend/app/models.py --checkpoint latest
```

Each checkpoint copies pristine sources into `.project_integrity/backups/<stamp>` so you can repair a single file (or the entire repo) without leaving VS Code. The manifest also stores `tags` and `milestone` metadata for downstream tooling.

## Tagging + comment standards

Every source file now follows a sectioned comment style:

```python
# --- Imports ---------------------------------------------------------------
# @tag:backend,api

# --- FastAPI application ---------------------------------------------------
```

Tags (documented in `docs/TAGS.md`) are parsed by the integrity CLI so Ops Deck, notebooks, and future automation can reason about ownership. When updating files, keep the section banners + `@tag:<name>` annotations intact so the ecosystem stays searchable and auditable.

## Contributing & next steps

1. Run `python scripts/project_integrity.py status` and commit only intentional changes.
2. Extend the data capture tests and DataLab notebooks with the provided templates.
3. Capture release notes via `python scripts/project_integrity.py checkpoint --tag release --reason "describe change"`.

Questions? Start with `PROJECT_OVERVIEW.md`, then dive into the docs above. This repo is intentionally verbose so every environment—from Codespaces to bare-metal servers—can reproduce the same experience.
