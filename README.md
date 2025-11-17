# ChatAI · DataLab - Change to Control Capsule(was PlayGround)

# This {
This {Instrument every keystroke inside ChatAI, relay it through FastAPI, and explore the signal-rich corpus in DataLab(KItchen). } (move to the recreated playground/capsule) This{ This mono-repo now ships with opinionated documentation, tagging standards, and an integrity toolchain so you can bootstrap, audit, and evolve the stack with confidence. We now treat each deployable trio of frontend + backend + DataLab(Kitchen) as a **Control Capsule**(was PlayGround)—the building block users clone to create their own environments.
}


> **Status:** Framework v1.0.0 is complete (snapshot 2025-11-15). Ongoing additions and milestone notes live in `docs/GOALS_AND_ACHIEVEMENTS.md` and the “Expanded Functionality” table inside `PROJECT_OVERVIEW.md`.
This {
## Why this project exists
This {
- **Full-fidelity capture** – pause telemetry, edit history, and prompt context stay linked to each inference. } (move to it's playground/capsule template)
- **Insight loop** – DataLab notebooks and scripts stay in-repo, keeping EDA reproducible.
- **Operational parity** – PowerShell + Bash control planes and Ops Deck widgets expose the same services/logs.
- **Governed change** – Hash-based integrity snapshots, checkpoints, and repair flows guard the codebase. } (is good, expand, more about Capsules, one shot prompt to capsule, etc)

## Feature highlights

| Area | Highlights |
| --- | --- |
| Frontend (`frontend`) | React + Vite command center with Prompt Recorder, Ops Deck, Tail log, Artifact shelf, dynamic themes, **new Elements canvas preview** |
| Backend (`backend`) | FastAPI relay, SQLAlchemy models, pluggable LLM client, artifact + tail-log APIs |
| Control plane (`controlplane/`) | Cross-platform orchestrator that powers the Ops Deck and CLI utilities |
| Kitchen (`kitchen/`) | Ready-to-run notebooks (see `hypothesis_control.ipynb`), metrics scripts, pinned requirements |
| Tooling | `scripts/setup.sh`, This{PowerShell `LabControl`, `labctl.sh`,} (change to CapControl & capctl) and the new `project_integrity.py` guards |

## Status tracker

| ✅ Completed | Notes |
| --- | --- |
| Full prompt instrumentation | `PromptRecorder.tsx` streams keystrokes, pauses, snapshots, and submits a single `/api/chat` payload without UI lag. |
| Unified FastAPI relay + storage | `/api/chat` validates payloads, calls the configured LLM adapter, and persists via `app/models.py` (interactions, artifacts, tail logs, elements). |
| DataLab parity | `datalab/notebooks/*` and `scripts/elements.py` mirror backend schemas, with Papermill tests keeping notebooks reproducible. |
| Ops tooling | PowerShell `LabControl`, Bash `labctl.sh`, and `project_integrity.py` provide consistent install/ops/integrity flows. |

| 🔎 Manual audit outcome | Details |
| --- | --- |
| TODO sweep | Searches across `chatai/frontend/src`, `chatai/backend/app`, and docs returned **no first-party `TODO` or "unimplemented" references** (SDK/vendor hits only). |
| Next candidates | Focus future work on §7 roadmap items: structured logging/observability, WebSocket streaming, managed DB migration, and reusable DataLab metric packages. |
This {
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
}(update)
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
4. **Control Center orchestration**:
   ```bash
   python scripts/control_center.py start
   python scripts/control_center.py playground   # optional UI entrypoint
   ```
5. **Integrity baseline**:
   ```bash
   python scripts/project_integrity.py init --reason "initial clone"
   ```
This {
## Working in the stack

- **Frontend dev server**: `cd chatai/frontend && npm install && npm run dev -- --host` (or use LabControl jobs).
- **Backend API**: `cd chatai/backend && .venv/Scripts/uvicorn app.main:app --reload`.
- **Ops Deck**: automatically polls `/api/ops/status` and surfaces controlplane actions. Tail logs funnel to both UI and DataLab notebook (#ops tag).
- **Control Center Playground**: `npm run playground:dev` inside `chatai/frontend` (or `python scripts/control_center.py playground`) to launch the multi-widget control UI backed by `/api/control/*` endpoints.
- **Control Center CLI**: `python scripts/control_center.py start|stop|status|notebook` controls Lab Orchestrator services, opens the Playground, or executes the new Papermill notebook without leaving the terminal. Use `python scripts/control_center.py elements catalog|validate|run` to list Elements nodes, validate graphs/presets, and execute DAGs locally via the shared GraphExecutor.
- **Storybook builds**: `npm run storybook:build` for the entire component catalog and `npm run storybook:playground` for the Control Center-only subset used in Chromatic/regression pipelines.
- **Hypothesis Workflow Control Lab notebook**: open `datalab/notebooks/hypothesis_control.ipynb` for experiment design, voting, telemetry charts, and ops log streaming.

## PowerShell search toolkit & observability

To avoid rewriting ad-hoc `Select-String` pipelines, reusable search presets now live in `scripts/powershell/SearchToolkit.psm1` with configuration in `scripts/powershell/search-presets.json`. Highlights:

1. **Load the module (any PowerShell host):**
   ```powershell
   Import-Module "$PSScriptRoot/scripts/powershell/SearchToolkit.psm1" -Force
   ```
2. **Run targeted searches:**
   ```powershell
   Invoke-RepoSearch -Pattern "TODO" -FileProfile python,frontend,docs
   Invoke-RepoSearch -Preset repo-todos -EmitStats
   Invoke-RepoSearch -Pattern "http(s)?://" -Regex -IncludeNodeModules -IncludeStorybook
   ```
3. **Inspect logs/history:** every invocation writes JSON lines to `logs/search-history.jsonl` (create the folder if missing). Use `Get-SearchHistory -Last 5` for a quick tail or `-Raw` for machine parsing.
4. **Preset catalog (curated sweeps):**

   | Preset | Purpose |
   | --- | --- |
   | `repo-todos` | Full-repo TODO scan honoring default excludes. |
   | `docs-todos` | Docs-only TODO sweep under `docs/`. |
   | `backend-unimplemented` | Look for "unimplemented" mentions across FastAPI. |
   | `frontend-debug-logs` | Flag `console.log`/`debugger` inside `chatai/frontend/src`. |
   | `backend-print-debug` | Catch stray `print(` calls in backend Python. |
   | `security-http-links` | Identify `http://` strings needing upgrade. |
   | `tests-skip-markers` | Surface `@pytest.mark.skip` / `pytest.skip` markers. |

5. **Extend or add your own:** append entries to `scripts/powershell/search-presets.json` (see `docs/OPS_COMMANDS.md §6` for field definitions and switch explanations).

For a ready-to-run example, execute the bundled script:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/powershell/examples/find-todos.ps1
```

Pass `-DryRun` or `-NoLog` to the script to preview filters or skip logging. This shared tooling keeps repo-wide TODO/unimplemented sweeps observable and repeatable.

Prefer a single entrypoint? The LabControl wrapper now proxies the same presets:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -SearchPreset repo-todos -EmitStats
pwsh -File scripts/lab-control.ps1 -SearchPattern "http://" -Regex -FileProfile frontend -IncludeNodeModules
```

When the JSONL history grows too large, call the Librarian helper to archive + prune before refreshing telemetry:

```powershell
pwsh -File scripts/lab-control.ps1 -RunSearchLibrarian -SearchHistoryOlderThanDays 30 -SearchHistoryKeep 2000 -RunSearchTelemetryIngestion
```

## Search telemetry ingestion & Ops Deck trends

- `datalab/scripts/search_telemetry.py ingest --log-path logs/search-history.jsonl --db-path data/search_telemetry.db` hydrates the JSONL search history into normalized SQLite tables (`search_runs`, `search_daily_metrics`).
- `pwsh -File scripts/lab-control.ps1 -RunSearchTelemetryIngestion` calls the same helper so Ops techs can refresh dashboards without leaving LabControl. Add `-SearchTelemetryLogPath` / `-SearchTelemetryDbPath` to target alternate paths.
- `datalab/notebooks/search_telemetry.ipynb` loads the SQLite file, charts daily sweep volume vs. findings, and highlights noisy presets. Pass `SEARCH_DB_PATH` (and optionally `TELEMETRY_LOG_PATH`) via Papermill or the Control Center notebook runner to keep CI deterministic.
- The ingestion job is idempotent: it hashes each JSON line before inserting, recomputes the daily aggregates, and emits the inserted/duplicate counts so Ops Deck tiles can track freshness.

Tie this into the Ops Deck by pointing the widgets at `data/search_telemetry.db`—they now have a steady feed of hygiene sweeps, match densities, and latency stats without reprocessing the raw JSON lines every time.

## Documentation suite

| Doc | Purpose |
| --- | --- |
| `docs/INSTALL.md` | OS-specific setup, verification, and troubleshooting |
| `docs/TUTORIALS.md` | Guided workflows for instrumentation → Ops Deck → DataLab insights |
| `docs/FILE_SYSTEM.md` | Official file tree, guardrails, naming and ownership rules |
| `docs/INTEGRITY.md` | Hash + checkpoint workflow, repair steps, metadata schema |
| `docs/TAGS.md` | Shared tagging standard for code comments, Ops Deck, and DataLab |
| `docs/RELEASE_CHECKLIST.md` | Pre-release gate list (tests, integrity, changelog, automation) |
| `docs/ELEMENTS_SPEC.md` | Architecture + scope for the Elements widget + node system |
| `docs/GOALS_AND_ACHIEVEMENTS.md` | Rolling log for completed milestones + in-flight additions |
| `docs/OPERATIONS_HANDBOOK.md` | Human-first overview of Control Capsules, workflows, releases, and troubleshooting |

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

To guard every push locally, wire up the provided Git hook:

```bash
cp scripts/git-hooks/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

The hook blocks outbound pushes if the integrity manifest is stale or if the Full Test Suite fails locally. Set `SKIP_PREPUSH_CHECKS=1` temporarily to bypass (for example when hotfixing from CI).

### Publishing Framework v1.0.0

When you're ready to stamp the current snapshot as `v1.0.0`, run the following from a clean `main` branch:

```bash
git checkout main
git pull --ff-only
python scripts/project_integrity.py status
git status
git tag -a v1.0.0 -m "Framework v1.0.0"
git push origin main
git push origin v1.0.0
```

These commands align with `docs/RELEASE_CHECKLIST.md` and ensure the annotated tag plus integrity manifest travel together.

Prefer a single entrypoint? Use LabControl:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -ReleaseBump patch -ReleasePipeline -ReleaseDryRun
pwsh -File scripts/lab-control.ps1 -ReleaseBump minor -ReleasePipeline -ReleaseChangelogTemplate docs/CHANGELOG_TEMPLATE.md -ReleaseChangelogSection Highlights -ReleaseChangelogSection Ops -ReleaseAsJob
pwsh -File scripts/lab-control.ps1 -ReleaseVersion 1.1.0 -ReleasePush -ReleaseFinalizeChangelog -ReleaseRunTests -ReleaseUpdateIntegrity
```

- `-ReleaseBump patch|minor|major` auto-derives the next semantic version from Git tags (defaults to patch when using `-ReleasePipeline`).
- `-ReleasePipeline` wraps `Publish-LabRelease` with the full checklist: changelog templating, test suite, integrity checkpoint, push, and optional background job execution (`-ReleaseAsJob`). Use `-ReleaseSkipChangelog`, `-ReleaseSkipTests`, or `-ReleaseSkipPush` for targeted dry runs.
- `-ReleaseChangelogTemplate docs/CHANGELOG_TEMPLATE.md -ReleaseChangelogSection <name>` injects structured sections into `CHANGELOG.md`, keeping Ops + DataLab notes aligned across releases.
- `-RunSearchTelemetryIngestion` can run before tagging so automation dashboards always reflect the latest hygiene sweep data.

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
4. Follow `docs/RELEASE_CHECKLIST.md` before tagging a release so GitHub artifacts always match the automation surface.
} {ensure is correct, remove mentions of chatai and datalab, etc. clean up, rework. reword. create a new milestone. i'm going to call it. backontrack. we acknowledge the work before, but we archieve the commits, description, goal etc, and concentrate on what we have implemented, goal of framework. possibilites etc. keep it mostly like now, but we just want an alignment bump. so everything can be in sync. a new baseline. a new begining, clean out the old)
Questions? Start with `PROJECT_OVERVIEW.md`, then dive into the docs above. This repo is intentionally verbose so every environment—from Codespaces to bare-metal servers—can reproduce the same experience.
