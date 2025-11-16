# Control Capsule Operations Handbook

> **Audience:** anyone who just cloned this repo, ops engineers wiring up releases, and builders crafting new capsules (frontend + backend + DataLab bundles).
>
> **Last updated:** 2025-11-16

This handbook distills how the ChatAI · DataLab workspace is organized, how we ship releases, and how to spin new environments ("control capsules") without losing the repo's power-user affordances. Keep this page open while coding—the sections link to scripts, docs, and workflows already living in the tree.

## 1. Purpose & vocabulary

| Term | Definition | Where to start |
| --- | --- | --- |
| **Platform** | The mono-repo itself: backend, frontend, control plane scripts, DataLab assets, docs, integrity tooling. | `README.md`, `docs/FILE_SYSTEM.md` |
| **Control Capsule** | A deployable trio consisting of a frontend control surface, backend guardrails/APIs, and a DataLab or notebook experience customized for a mission. Capsules run locally or remotely via the Control Center. | This document §4 + §5 |
| **Ops Deck** | The built-in monitoring UI (Control Center Playground + Storybook surfaces) that proves a capsule is healthy. | `chatai/frontend`, `docs/STABILITY_WORKFLOW.md` |
| **Integrity Stack** | `scripts/project_integrity.py`, checkpoints, backups, and the release guardrails that keep artifacts + hashes aligned. | `docs/INTEGRITY.md`, this document §7 |

Our near-term goal is to let anyone install the repo and immediately launch a capsule that helps them set up new capsules—bootstrapping the workspace itself. Every change in this release leans toward that self-hosting loop.

## 2. Repo structure at a glance

| Area | Tech stack | Typical changes |
| --- | --- | --- |
| `chatai/backend` | FastAPI, SQLAlchemy, Pydantic | Guardrails, command/search services, adapters, storage schemas |
| `chatai/frontend` | React + Vite + TypeScript + Storybook | Ops Deck widgets, control center flows, design system blueprints |
| `datalab` | Jupyter/Papermill, pandas, Plotly/Altair, rich CLI helpers | Notebook templates, telemetry ingestion, widgets, diagnostics |
| `scripts` | Python CLIs + PowerShell/Bash orchestrators | Control Center automation, release helpers, LabControl presets |
| `controlplane` | Python orchestrator for job scheduling | Multi-service coordination, CLI bridging |
| `docs` | Markdown playbooks | Workflow explanations, guardrails, onboarding | 

When in doubt: find the owning doc inside `docs/` (e.g., `docs/ELEMENTS_SPEC.md` for the frontend graph system) before editing code.

## 3. Two work modes

1. **Platform maintenance** – Keeping the mono-repo itself healthy. Typical tasks: refactor a FastAPI route, upgrade npm dependencies, extend notebook tests, refresh docs.
2. **Capsule authorship** – Using the repo to create a new environment instance. Tasks: duplicate a capsule template, wire mission-specific widgets/notebooks, run the Control Center to monitor it, ship assets to operators.

Treat these modes separately: finish platform housekeeping (tests, integrity, docs) before cloning capsules. Each capsule inherits the quality of the platform snapshot you start from.

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
3. **Open DataLab**
   ```powershell
   cd datalab
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

## 5. Crafting a Control Capsule

```
Capsule = Frontend control surface + Backend guardrails + DataLab notebook suite
```

1. **Name it** – use `capsule-<purpose>` (e.g., `capsule-ops-health`).
2. **Clone the template** – copy `chatai/frontend/src/control-center/templates/capsuleStarter`, the corresponding FastAPI blueprint in `chatai/backend/app/api/capsules`, and the notebook preset under `datalab/notebooks/templates` (create these folders if missing).
3. **Wire services**
   - Frontend: import new widgets into `chatai/frontend/src/control-center/registry.ts` and expose toggles in Storybook.
   - Backend: register the capsule router in `app/main.py`, add persistence (SQLite or Cosmos-ready) via `app/models.py`.
   - DataLab: duplicate an existing notebook (Search Telemetry, Ops Response Playbook, Widget Showcase) and update parameters at the top so Papermill + Control Center can submit runs.
4. **Control plane hook-up** – add commands to `scripts/lab-control.ps1` (PowerShell) and `labctl.sh` (bash) so operators can start/stop or ingest data for this capsule.
5. **Document it** – append a short blurb to `docs/OPERATIONS_HANDBOOK.md §9` (“Capsule catalog”) and reference the owning tests.

## 6. Workflow for contributing code

| Phase | Checklist |
| --- | --- |
| Plan | Update `docs/GOALS_AND_ACHIEVEMENTS.md` → “Ongoing Additions”. Reference tags/owners. |
| Build | Follow area-specific guides (`docs/ELEMENTS_SPEC.md`, backend README, DataLab tests). Keep sections + `@tag:` annotations intact. |
| Validate | Run targeted suites: `pytest chatai/backend`, `npm run test`, `python -m pytest datalab/tests`, `python -m pytest tests/test_notebooks.py`. Use LabControl’s `-ReleaseRunTests` wrapper when batching. |
| Freeze | `python scripts/project_integrity.py status --baseline <last-tag>` to see exactly what changed since the previous release checkpoint. Expect zero surprises before you checkpoint. |
| Release | See §7. |

## 7. Release & integrity essentials

1. **Diff vs. previous release**
   ```powershell
   python scripts/project_integrity.py status --baseline v1.0.1-stability.20251116
   ```
   - Accepts checkpoint ids (e.g., `0002`) or git tags (falls back to `git show tag:.project_integrity/index.json`).
2. **Run `scripts/release_checklist.ps1`** (or follow `docs/RELEASE_CHECKLIST.md`). This executes backend + frontend + DataLab suites, Papermill snapshots, and telemetry ingestion.
3. **Artifacts to attach every time**
   - `chatai/frontend/dist/` (zip it as `control-center-dist.zip`).
   - `chatai/frontend/storybook-static/` and `storybook-static-playground/` (zip individually).
   - Papermill outputs for Search Telemetry, Ops Response Playbook, Widget Showcase (`datalab/notebooks/_papermill/*`).
   - Generated scripts: `scripts/lab-bootstrap.ps1`, `scripts/release_checklist.ps1`, plus any new `LabControl` modules touched.
4. **Release notes**
   - Call out the three grouped commits (backend hardening, frontend design system, DataLab bundle) with links to PRs or commit hashes.
   - Link to the notebooks + scripts above so operators can replay the evidence.
5. **Checkpoint**
   ```powershell
   python scripts/project_integrity.py checkpoint --tag v1.0.2 --reason "capsule refresh"
   ```

## 8. Running & debugging services

| Need | Command |
| --- | --- |
| Tail orchestrator logs | `pwsh -File scripts/lab-control.ps1 -TailControlPlane` |
| Restart backend | `pwsh -File scripts/lab-control.ps1 -RestartBackend` or `uvicorn app.main:app --reload` |
| Inspect sqlite | `python -m sqlite3 data/interactions.db '.tables'` |
| Monitor search telemetry ingestion | `pwsh -File scripts/lab-control.ps1 -RunSearchTelemetryIngestion -Verbose` |
| Rebuild Storybook | `cd chatai/frontend && npm run storybook:build && npm run storybook:playground` |
| Notebook smoke | `python -m pytest tests/test_notebooks.py -k <name>` |

If something drifts, use `python scripts/project_integrity.py verify <path>` to confirm hashes, or `repair --checkpoint latest` to restore.

## 9. Capsule catalog & ideas

| Capsule | Purpose | Components |
| --- | --- | --- |
| **Ops Response Playbook** | Walks incident responders through triage checklists while streaming telemetry into notebooks. | Notebook: `datalab/notebooks/ops_response_playbook.ipynb`; Frontend widget: Ops Playbook tile; Backend: `/api/ops/playbook`. |
| **Search Telemetry Deck** | Visualizes hygiene sweeps and raises regressions. | Notebook + ingestion script described in §7. |
| **Widget Showcase** | Sandbox for new Elements nodes + design tokens. | Storybook stories + `widget_showcase.ipynb`. |
| **Bootstrap Capsule** *(planned default)* | Launches on a fresh install to help the user configure credentials, run tests, and author their first custom capsule. | TODO – track in `docs/GOALS_AND_ACHIEVEMENTS.md`. |

## 10. Future: saving & loading environments

Upcoming goals:

1. **Capsule manifests** – JSON descriptors living in `configs/capsules/*.json` describing which services + notebooks to load.
2. **State snapshots** – `project_integrity.py export` + zipped DataLab states stored under `backups/capsules/<name>`.
3. **LabControl verbs** – `-CapsuleSave <name>` / `-CapsuleLoad <name>` wrapping the manifest + snapshot copy.
4. **Default onboarding capsule** – shipped in `capsules/bootstrap/` and loaded by LabControl after `-Bootstrap` completes.

Track progress for these items in the goals log (§11) and treat this document as the canonical spec until we cut a separate `capsules/` README.

## 11. Tips, issue hunting, and references

- **Hunt regressions** – run `Invoke-RepoSearch -Preset repo-todos` (PowerShell) or `python -m scripts.project_integrity verify` before committing.
- **Papermill outputs** – never commit `_papermill` outputs; instead, upload them to releases. The repo now enforces this by default (`git rm --cached` already applied).
- **Docs to read next**:
  - `docs/STABILITY_WORKFLOW.md` for freeze logic.
  - `docs/RELEASE_CHECKLIST.md` for step-by-step gating.
  - `docs/TUTORIALS.md` for mini-project walkthroughs.
  - `docs/TAGS.md` to understand the tag taxonomy referenced throughout this handbook.

By following this handbook you can treat the repo as "click and play" without giving up the fine-grained control ops engineers expect. When you improve a workflow, come back here, document the change, and point to the owning automation so the next maintainer inherits a complete system.
