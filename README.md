# ChatAI · Playground Framework

Instrument every keystroke inside ChatAI, relay it through FastAPI, and explore the signal-rich corpus inside the Kitchen (formerly DataLab). This mono-repo now ships with opinionated documentation, tagging standards, and an integrity toolchain so you can bootstrap, audit, and evolve the stack with confidence. We now treat each deployable trio of frontend + backend + Kitchen as a **Playground** packaged inside a Control Capsule—the building block users clone to create their own environments.

> **Status:** Framework v1.0.0 is complete (snapshot 2025-11-15). Ongoing additions and milestone notes live in `docs/GOALS_AND_ACHIEVEMENTS.md`, the “Expanded Functionality” table inside `PROJECT_OVERVIEW.md`, and the new `docs/PLAYGROUND_GUIDE.md`.

## Why this project exists

- **Full-fidelity capture** – pause telemetry, edit history, and prompt context stay linked to each inference.
- **Kitchen-first insight loop** – Recipes and Cookbooks stay in-repo, keeping experimentation reproducible.
- **Operational parity** – PowerShell + Bash control planes and Ops Deck widgets expose the same services/logs.
- **Governed change** – Hash-based integrity snapshots, checkpoints, and repair flows guard the codebase.

## Playground anatomy

| Layer | Focus | Responsibilities |
| --- | --- | --- |
| **Frontend (Control Surface)** | UI + interactions | Render layouts authored in Recipes, display telemetry, accept operator input with minimal business logic. |
| **Backend (Orchestration)** | APIs + safety | Serve the frontend, validate Recipe manifests, wire data sources, enforce tenant isolation, stream live updates. |
| **Kitchen (Notebook Designer)** | System definition | Author Recipes/Cookbooks, bind widgets to data, script workflows, and push manifests that hot-reload the frontend. |

Creating a Playground means designing in the Kitchen, syncing through the backend, and observing from the frontend. See `docs/PLAYGROUND_GUIDE.md` for detailed flows.

## Feature highlights

| Area | Highlights |
| --- | --- |
| Frontend (`playground/frontend`) | React + Vite control surface with Prompt Recorder, Ops Deck, Tail log, Artifact shelf, dynamic themes, **manifest-driven preview panel**, and the new Elements canvas preview |
| Backend (`playground/backend`) | FastAPI relay, SQLAlchemy models, pluggable LLM client, artifact + tail-log APIs, Playground manifest router |
| Control plane (`controlplane/`) | Cross-platform orchestrator that powers the Ops Deck and CLI utilities |
| Kitchen (`kitchen/`; historical copies under `legacy/datalab/`) | Notebooks, Recipes, metrics scripts, pinned requirements, and Cookbooks that design Playgrounds |
| Tooling | `scripts/setup.sh`, PowerShell `LabControl`, `labctl.sh`, and the new `project_integrity.py` guards |

## Status tracker

| ✅ Completed | Notes |
| --- | --- |
| Full prompt instrumentation | `PromptRecorder.tsx` streams keystrokes, pauses, snapshots, and submits a single `/api/chat` payload without UI lag. |
| Unified FastAPI relay + storage | `/api/chat` validates payloads, calls the configured LLM adapter, and persists via `app/models.py` (interactions, artifacts, tail logs, elements). |
| Kitchen (formerly DataLab) parity | `kitchen/notebooks/*` now source every Papermill run; the `legacy/datalab` tree remains read-only for historical notebooks. `scripts/elements.py` mirrors backend schemas so Recipes stay reproducible. |
| Ops tooling | PowerShell `LabControl`, Bash `labctl.sh`, and `project_integrity.py` provide consistent install/ops/integrity flows. |

| 🔎 Manual audit outcome | Details |
| --- | --- |
| TODO sweep | Searches across `playground/frontend/src`, `playground/backend/app`, and docs returned **no first-party `TODO` or "unimplemented" references** (SDK/vendor hits only). |
| Next candidates | Focus future work on §7 roadmap items: structured logging/observability, WebSocket streaming, and reusable Kitchen metric packages. Cosmos DB and SQLite support are already implemented and runtime selectable. |

## Repository map

```
playground/     # frontend + backend source
controlplane/   # ops/orchestration helpers
scripts/        # installers + job control
scripts/powershell/  # Windows control center
scripts/project_integrity.py  # hash + checkpoint CLI
configs/        # manifests, tagging + guardrail config
backups/        # integrity snapshots land here
kitchen/        # active notebooks + analysis assets
legacy/datalab/ # read-only historical notebooks copied from the pre-Kitchen era
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
- **Kitchen**:
   ```bash
   cd kitchen
   python -m venv .venv  # if missing
   . .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
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

## Working in the stack

- **Frontend dev server**: `cd playground/frontend && npm install && npm run dev -- --host` (or use LabControl jobs).
- **Backend API**: `cd playground/backend && .venv/Scripts/uvicorn app.main:app --reload`.
- **Ops Deck**: automatically polls `/api/ops/status` and surfaces controlplane actions. Tail logs funnel to both UI and Kitchen notebooks (#ops tag).
- **Control Center Playground**: `npm run playground:dev` inside `playground/frontend` (or `python scripts/control_center.py playground`) to launch the multi-widget control UI backed by `/api/control/*` endpoints.
- **Playground manifest preview**: set `VITE_PLAYGROUND_TENANT` / `VITE_PLAYGROUND_NAME` (defaults to `demo-tenant/welcome-control`) in `playground/frontend/.env` to point the UI at your namespace. The manifest surfaces now run through `ManifestProvider`, exposing manual refresh + auto-refresh toggles, tail-log sync traces, and a widget/action summary card inside the intel stack.
- **Storybook manifest knobs**: `npm run storybook` exposes dedicated `Manifest/*` stories with controls for tenant/playground metadata, section layouts, and action lists so reviewers can simulate Kitchen revisions without publishing.
- **Manifest validation CLI**: `python scripts/manifest_validator.py path/to/manifest.json --json` runs the Pydantic validator and prints MCP-friendly summaries (use `-` to read JSON from stdin; add `--expect-tenant/--expect-playground` to pin namespaces). The same command now ships in the Control Center command catalog as **“Manifest validator (onboarding)”**, so MCP agents can trigger it without leaving the Ops Deck.
- **Frontend lint/type-check**: `npm run check` runs ESLint plus `tsc --noEmit` so you can gate PRs locally before the CI jobs (`frontend-qa`, `storybook-builds`) run.
- **Control Center CLI**: `python scripts/control_center.py start|stop|status|notebook` controls Lab Orchestrator services, opens the Playground, or executes the new Papermill notebook without leaving the terminal. Use `python scripts/control_center.py elements catalog|validate|run` to list Elements nodes, validate graphs/presets, and execute DAGs locally via the shared GraphExecutor.
- **Storybook builds**: `npm run storybook:build` for the entire component catalog and `npm run storybook:playground` for the Control Center-only subset used in Chromatic/regression pipelines.
- **Chromatic snapshots**: export `CHROMATIC_PROJECT_TOKEN` and run `npm run chromatic` (wraps the Control Center-only Storybook build plus Chromatic upload with `exitZeroOnChanges` so Ops smoke tests can run locally or in CI without flaking on diffs).
- **Kitchen Recipes & Cookbooks**: start with `kitchen/notebooks/welcome_cookbook.ipynb` (this notebook) plus the archived `legacy/datalab` copies for historical reference when migrating assets.

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
   | `frontend-debug-logs` | Flag `console.log`/`debugger` inside `playground/frontend/src`. |
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

- `python scripts/search_telemetry.py ingest --log-path logs/search-history.jsonl --output data/search_telemetry.json --runs-parquet data/search_telemetry-runs.parquet --daily-parquet data/search_telemetry-daily.parquet` hydrates the JSONL search history into a manifest-friendly ledger, emits optional Parquet extracts for analytics tooling, and embeds run-level details, daily aggregates, and preset drift stats.
- `pwsh -File scripts/lab-control.ps1 -RunSearchTelemetryIngestion` calls the same entrypoint so Ops techs can refresh dashboards without leaving LabControl. Override defaults with `-SearchTelemetryLogPath`, `-SearchTelemetryOutputPath`, or the legacy `-SearchTelemetryDbPath` shim if you're migrating artifacts.
- `kitchen/notebooks/search_telemetry.ipynb` loads the JSON ledger, charts daily sweep volume vs. findings, and highlights noisy presets. Pass `SEARCH_LEDGER_PATH` (and optionally `TELEMETRY_LOG_PATH`) via Papermill or the Control Center notebook runner to keep CI deterministic.
- The ingestion job is idempotent: it hashes each JSON line before writing the ledger, recomputes aggregates, and emits inserted/duplicate counts so Ops Deck tiles can track freshness.

Parquet exports rely on the optional `pyarrow` dependency (`pip install -r kitchen/requirements.txt`). Pass `--no-tail-log` if you need to silence tail-log emissions during offline runs.

Tie this into the Ops Deck by pointing the widgets at `data/search_telemetry.json`—they now have a steady feed of hygiene sweeps, match densities, and latency stats without reprocessing the raw JSON lines every time.

## Documentation suite

| Doc | Purpose |
| --- | --- |
| `docs/INSTALL.md` | OS-specific setup, verification, and troubleshooting |
| `docs/TUTORIALS.md` | Guided workflows for instrumentation → Ops Deck → Kitchen Recipes |
| `docs/FILE_SYSTEM.md` | Official file tree, guardrails, naming and ownership rules |
| `docs/INTEGRITY.md` | Hash + checkpoint workflow, repair steps, metadata schema |
| `docs/TAGS.md` | Shared tagging standard for code comments, Ops Deck, and Kitchen assets |
| `docs/RELEASE_CHECKLIST.md` | Pre-release gate list (tests, integrity, changelog, automation) |
| `docs/ELEMENTS_SPEC.md` | Architecture + scope for the Elements widget + node system |
| `docs/PLAYGROUND_GUIDE.md` | Definitions for Playgrounds, Kitchen, Recipes, and Cookbooks |
| `docs/GOALS_AND_ACHIEVEMENTS.md` | Rolling log for completed milestones + in-flight additions |
| `docs/OPERATIONS_HANDBOOK.md` | Human-first overview of Control Capsules, workflows, releases, and troubleshooting |
| `docs/AGENT_OPERATIONS.md` | Agent-specific scripts, manifest workflows, and MCP tooling expectations |

## Integrity + versioning guardrails

`scripts/project_integrity.py` keeps a manifest of every tracked file (hash, size, tags, timestamps) under `.project_integrity/index.json`. Core commands:

```
python scripts/project_integrity.py init --reason "Initial baseline"
python scripts/project_integrity.py status                     # diff vs. manifest
python scripts/project_integrity.py checkpoint --tag release --reason "0.2.0"
python scripts/project_integrity.py verify playground/backend/app/models.py
python scripts/project_integrity.py repair playground/backend/app/models.py --checkpoint latest
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
- `-ReleaseChangelogTemplate docs/CHANGELOG_TEMPLATE.md -ReleaseChangelogSection <name>` injects structured sections into `CHANGELOG.md`, keeping Ops + Kitchen notes aligned across releases.
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
2. Extend the data capture tests and Kitchen notebooks with the provided templates (only reference `legacy/datalab` when you need historical context).
3. Capture release notes via `python scripts/project_integrity.py checkpoint --tag release --reason "describe change"`.
4. Follow `docs/RELEASE_CHECKLIST.md` before tagging a release so GitHub artifacts always match the automation surface.

Questions? Start with `PROJECT_OVERVIEW.md`, then dive into the docs above. This repo is intentionally verbose so every environment—from Codespaces to bare-metal servers—can reproduce the same experience.
