# Horizon Relay Operations Handbook

> **Audience:** anyone who just cloned this repo, ops engineers wiring up releases, and builders crafting new relays (frontend + backend + Workshop bundles).
>
> **Last updated:** 2025-11-16

This handbook distills how the ChatAI · Workshop workspace is organized, how we ship releases, and how to spin new environments ("horizon relays") without losing the repo's power-user affordances. Keep this page open while coding—the sections link to scripts, docs, and workflows already living in the tree.

## Quick-start scripts

| Task | Command | Notes |
| --- | --- | --- |
| Launch Control Center relay | `npm run relay:dev` (from `relay/frontend`) | Hydrates UI via `ManifestProvider`; set `.env` `VITE_RELAY_TENANT`/`VITE_RELAY_NAME`. |
| Run Ops orchestrator helpers | `python scripts/control_center.py <command>` | Supports `start`, `stop`, `status`, `notebook`, `elements`; emits telemetry under `data/logs`. |
| Publish Workshop manifest | `python workshop/scripts/publish_manifest.py --tenant <id> --relay <name>` | Wraps `ManifestPublisher` helper to calculate checksums + revisions. |
| Validate manifest locally | `python scripts/manifest_validator.py manifests/sample.json --json` | Uses the Pydantic schema and emits MCP-friendly JSON summaries. |
| Notebook snapshot (Papermill) | `python scripts/control_center.py notebook --db-path auto` | Runs `control_center_relay.ipynb` with datastore auto-wiring; outputs land in `workshop/notebooks/_papermill`. |
| Inspect datastore provider | `python scripts/relay_store.py summary` | Works across SQLite/JSON/Cosmos providers; pair with `tail-log` and `tail-log-add`. |
| Freeze → tag pipeline | `python scripts/release_pipeline.py --tag vYYYYMMDD-HHMMSS-control-relays` | One-command release: runs tests, validates manifests, enforces integrity, checkpoints, tags, pushes, and logs telemetry (`--dry-run`, `--allow-dirty`, `--skip-tests`, `--skip-integrity`, `--force-release-dir`, `--no-push`) and now accepts `--notes "context"` to embed why the release exists. |
| Change history database | `python scripts/change_runs.py list` / `show <id>` / `new --title ...` | Browse or scaffold optional `/changes` reports. Intended for agent-authored narratives; no build/release step depends on it. |

## 1. Purpose & vocabulary

| Term | Definition | Where to start |
| --- | --- | --- |
| **Platform** | The mono-repo itself: backend, frontend, control plane scripts, Workshop assets, docs, integrity tooling. | `README.md`, `docs/FILE_SYSTEM.md` |
| **Horizon Relay** | A deployable trio consisting of a frontend control surface, backend guardrails/APIs, and a Workshop notebook experience customized for a mission. Relays run locally or remotely via the Control Center. | This document §4 + §5 |
| **Ops Deck** | The built-in monitoring UI (Control Center Relay + Storybook surfaces) that proves a relay is healthy. | `relay/frontend`, `docs/STABILITY_WORKFLOW.md` |
| **Integrity Stack** | `scripts/project_integrity.py`, checkpoints, backups, and the release guardrails that keep artifacts + hashes aligned. | `docs/INTEGRITY.md`, this document §7 |

Our near-term goal is to let anyone install the repo and immediately launch a relay that helps them set up new relays—bootstrapping the workspace itself. Every change in this release leans toward that self-hosting loop.

## 2. Repo structure at a glance

| Area | Tech stack | Typical changes |
| --- | --- | --- |
| `relay/backend` | FastAPI, SQLAlchemy, Pydantic | Guardrails, command/search services, adapters, storage schemas |
| `relay/frontend` | React + Vite + TypeScript + Storybook | Ops Deck widgets, control center flows, design system blueprints |
| `workshop` | Jupyter/Papermill, pandas, Plotly/Altair, rich CLI helpers | Notebook templates, telemetry ingestion, widgets, diagnostics |
| `scripts` | Python CLIs + PowerShell/Bash orchestrators | Control Center automation, release helpers, LabControl presets |
| `controlplane` | Python orchestrator for job scheduling | Multi-service coordination, CLI bridging |
| `docs` | Markdown playbooks | Workflow explanations, guardrails, onboarding | 

When in doubt: find the owning doc inside `docs/` (e.g., `docs/ELEMENTS_SPEC.md` for the frontend graph system) before editing code.

## 3. Two work modes

1. **Platform maintenance** – Keeping the mono-repo itself healthy. Typical tasks: refactor a FastAPI route, upgrade npm dependencies, extend notebook tests, refresh docs.
2. **Relay authorship** – Using the repo to create a new environment instance. Tasks: duplicate a relay template, wire mission-specific widgets/notebooks, run the Control Center to monitor it, ship assets to operators.

Treat these modes separately: finish platform housekeeping (tests, integrity, docs) before cloning relays. Each relay inherits the quality of the platform snapshot you start from.

## 4. Getting set up quickly

1. **Clone + bootstrap**
   ```powershell
   git clone https://github.com/nihilistau/ChatAI-DataLab.git
   cd ChatAI-DataLab
   pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -Bootstrap
   ```
2. **Spin the Control Center** (opens the Ops Deck + API relay)
   ```powershell
   pwsh -File scripts/lab-control.ps1 -ControlCenter
   ```
3. **Open the Workshop workspace**
   ```powershell
   cd workshop
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   jupyter lab --notebook-dir notebooks
   ```
4. **Verify integrity**
   ```powershell
   python scripts/project_integrity.py status
   ```
5. **Optional:** tag your baseline right away so `status --baseline <tag>` works later (see §7).

## 5. Crafting a Horizon Relay

```
Relay = Frontend control surface + Backend guardrails + Workshop notebook suite
```

1. **Name it** – use `relay-<purpose>` (e.g., `relay-ops-health`).
2. **Clone the template** – copy `relay/frontend/src/control-center/templates/relayStarter`, the corresponding FastAPI blueprint in `relay/backend/app/api/relays`, and the notebook preset under `workshop/notebooks/` (duplicate an existing notebook such as Search Telemetry or Ops Response as your starting point).
3. **Wire services**
   - Frontend: import new widgets into `relay/frontend/src/control-center/registry.ts` and expose toggles in Storybook.
   - Backend: register the relay router in `app/main.py` and persist through the datastore abstraction (`app/services/data_store.py:data_store_context`). Providers (SQLite, JSON artifacts, Cosmos DB) are runtime selectable via `configs/lab_environment_config.md`, so avoid hard-coded paths.
   - Workshop: duplicate an existing notebook (Search Telemetry, Ops Response Playbook, Widget Showcase) and parameterize it with `DB_PATH="auto"` + helpers such as `workshop.scripts.metrics.load_interactions()` so Papermill + Control Center automatically talk to the active provider.
4. **Control plane hook-up** – add commands to `scripts/lab-control.ps1` (PowerShell) and `labctl.sh` (bash) so operators can start/stop or ingest data for this relay.
5. **Document it** – append a short blurb to `docs/OPERATIONS_HANDBOOK.md §9` (“Relay catalog”) and reference the owning tests.

### Datastore & telemetry guardrails

- The Relay data store is configured via `configs/lab_environment_config.md` and surfaced everywhere through `relay/backend/app/services/data_store.py`. Providers can be swapped (SQLite, JSON snapshots, Cosmos DB) without touching relay code as long as you call the shared helpers.
- Inspect or mutate the active store with `python scripts/relay_store.py summary|interactions|artifacts|tail-log`. These commands respect the provider config and keep operators out of raw SQLite shells.
- Papermill workflows should run through `python scripts/control_center.py notebook --db-path auto`, which injects the right credentials and keeps notebooks portable. Manual notebook runs should also default `DB_PATH="auto"` so they reuse the store abstraction.
- Every manifest consumer must log lifecycle events. Prefer `createTailLogEntry` / `appendTailLog` (frontend) or the CLI’s `tail-log-add` subcommand so Ops sees datastore churn, notebook runs, and relay refreshes in the Control Center tail log.

## 6. Workflow for contributing code

| Phase | Checklist |
| --- | --- |
| Plan | Update `docs/GOALS_AND_ACHIEVEMENTS.md` → “Ongoing Additions”. Reference tags/owners. |
| Build | Follow area-specific guides (`docs/ELEMENTS_SPEC.md`, backend README, Workshop tests). Keep sections + `@tag:` annotations intact. |
| Validate | Run targeted suites: `pytest relay/backend`, `npm run test`, `python -m pytest workshop/tests`, `python -m pytest tests/test_notebooks.py`. Use LabControl’s `-ReleaseRunTests` wrapper when batching. |
| Freeze | `python scripts/project_integrity.py status --baseline <last-tag>` to see exactly what changed since the previous release checkpoint. Expect zero surprises before you checkpoint. |
| Release | See §7. |

## 7. Release & integrity essentials

1. **Diff vs. previous release**
   ```powershell
   python scripts/project_integrity.py status --baseline v1.0.1-stability.20251116
   ```
   - Accepts checkpoint ids (e.g., `0002`) or git tags (falls back to `git show tag:.project_integrity/index.json`).
2. **Run `scripts/release_checklist.ps1`** (or follow `docs/RELEASE_CHECKLIST.md`). This executes backend + frontend + Workshop suites, Papermill snapshots, and telemetry ingestion.
3. **Artifacts to attach every time**
   - `relay/frontend/dist/` (zip it as `control-center-dist.zip`).
   - `relay/frontend/storybook-static/` and `storybook-static-relay/` (zip individually).
   - Papermill outputs for Search Telemetry, Ops Response Playbook, Widget Showcase (`workshop/notebooks/_papermill/*`).
   - Generated scripts: `scripts/lab-bootstrap.ps1`, `scripts/release_checklist.ps1`, plus any new `LabControl` modules touched.
4. **Release notes**
   - Call out the three grouped commits (backend hardening, frontend design system, Workshop bundle) with links to PRs or commit hashes.
   - Link to the notebooks + scripts above so operators can replay the evidence.
5. **Checkpoint**
   ```powershell
   python scripts/project_integrity.py checkpoint --tag v1.0.2 --reason "relay refresh"
   ```

## 8. Running & debugging services

| Need | Command |
| --- | --- |
| Tail orchestrator logs | `pwsh -File scripts/lab-control.ps1 -TailControlPlane` |
| Restart backend | `pwsh -File scripts/lab-control.ps1 -RestartBackend` or `uvicorn app.main:app --reload` |
| Inspect datastore provider | `python scripts/relay_store.py summary` |
| Tail/store telemetry | `python scripts/relay_store.py tail-log --limit 40` |
| Papermill Control Center run | `python scripts/control_center.py notebook --db-path auto` |
| Monitor search telemetry ingestion | `pwsh -File scripts/lab-control.ps1 -RunSearchTelemetryIngestion -Verbose` |
| Rebuild Storybook | `cd relay/frontend && npm run storybook:build && npm run storybook:relay` |
| Notebook smoke | `python -m pytest tests/test_notebooks.py -k <name>` |

If something drifts, use `python scripts/project_integrity.py verify <path>` to confirm hashes, or `repair --checkpoint latest` to restore.

## 9. Relay catalog & ideas

| Relay | Purpose | Components |
| --- | --- | --- |
| **Ops Response Playbook** | Walks incident responders through triage checklists while streaming telemetry into notebooks. | Notebook: `workshop/notebooks/ops_response_playbook.ipynb`; Frontend widget: Ops Playbook tile; Backend: `/api/ops/playbook`. |
| **Search Telemetry Deck** | Visualizes hygiene sweeps and raises regressions. | Notebook + ingestion script described in §7. |
| **Widget Showcase** | Sandbox for new Elements nodes + design tokens. | Storybook stories + `widget_showcase.ipynb`. |
| **Bootstrap Relay** *(default onboarding)* | Launches on a fresh install to help the user configure credentials, run tests, and author their first custom relay. | Manifest: `configs/relays/onboarding.json`; Save/load verbs: `Save-LabRelay`, `Load-LabRelay` (PowerShell), `relay_control.py` (Python CLI); Persistence: auto-snapshot/load hooks. |


## 10. Saving & loading environments

### Relay manifests
Relay manifests are JSON descriptors in `configs/relays/*.json` (see `onboarding.json`) that declare environment, notebooks, and state fields. These power onboarding and custom relay launches.

### State snapshots
Relay state is snapshotted via:
- PowerShell: `Save-LabRelay` and `Load-LabRelay` (see `LabControl.psm1`)
- Python CLI: `python workshop/scripts/relay_control.py save|load`
Snapshots are stored in `data/relay-onboarding-snapshot.json` (or a timestamped backup).

### Persistence hooks
Auto-snapshot logic can be added to LabControl and Workshop scripts to save state after key events (run, config change, notebook execution) and restore on launch. Reference `legacy/datalab` only when reviewing historical snapshots.

### Onboarding workflow
On fresh install, LabControl loads the onboarding relay manifest, restores any previous state, and launches the Control Center. Users can save/load their environment at any time using the verbs above.

Track progress for these items in the goals log (§11) and treat this document as the canonical spec until a separate `relays/` README is created.

## 11. Tips, issue hunting, and references

- **Hunt regressions** – run `Invoke-RepoSearch -Preset repo-todos` (PowerShell) or `python -m scripts.project_integrity verify` before committing.
- **Papermill outputs** – never commit `_papermill` outputs; instead, upload them to releases. The repo now enforces this by default (`git rm --cached` already applied).
- **Docs to read next**:
  - `docs/STABILITY_WORKFLOW.md` for freeze logic.
  - `docs/RELEASE_CHECKLIST.md` for step-by-step gating.
  - `docs/TUTORIALS.md` for mini-project walkthroughs.
  - `docs/TAGS.md` to understand the tag taxonomy referenced throughout this handbook.

By following this handbook you can treat the repo as "click and play" without giving up the fine-grained control ops engineers expect. When you improve a workflow, come back here, document the change, and point to the owning automation so the next maintainer inherits a complete system.
