# Changelog

All notable changes to this repository will be documented in this file. The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the repo follows semantic versioning.

## [Unreleased]

### Added
- Control Center CLI support for the config-driven rebrand workflow via `python scripts/control_center.py rebrand` plus Control Center command palette entries (`Rebrand · dry run`, `Rebrand · apply plan`).
- Ops workflow harness (`scripts/workflow_harness.py`) that chains release dry-run, goals log entry, change record scaffolding, integrity checkpointing, and rebrand dry-run — also exposed through `python scripts/control_center.py workflow` and the Ops Deck command catalog.
- Timeline export flags (`--timeline-json`, `--timeline-jsonl`) for the workflow harness so Ops Deck + MCP tooling can ingest structured run results under `data/logs/workflow_harness/`.
- Tail-log + release-log telemetry for the Ops workflow harness (new `--tail-log-source`, `--tail-log-message`, `--skip-tail-log`, `--skip-release-log` options) so every composite run shows up in the datastore tail log and `data/logs/release.log` by default.

### Changed
- `scripts/control_center.py` now points the relay helper at `relay/frontend` and forwards arguments to `scripts/rebrand_reset.py`.
- `docs/AGENT_OPERATIONS.md` documents the new CLI/MCP entry points and keeps the rebrand section aligned with current automation.
- `data/commands.json` gains an "Ops workflow harness" entry so the entire release/doc/rebrand combo can run from the Ops Deck without shell access.

## [1.0.1] - 2025-11-16

### Added
- Stability workflow playbook and syntax guardrails documenting the freeze process (`docs/STABILITY_WORKFLOW.md`, `syntax.md`).
- Scheduled Search Toolkit sweep workflow plus artifacts for automated bug-hunt + log-review passes (`.github/workflows/search-toolkit-sweep.yml`).
- Ops design system showcase content and notebook safety net enhancements captured inside `tests/test_notebooks.py` and Papermill outputs.

### Changed
- Elements API guardrail endpoint now accepts optional payloads so max-run enforcement returns `429` instead of validation errors (`relay/backend/app/api/elements.py`).
- Notebook regressions now install the Workshop requirements set (Plotly, ipywidgets, visualization deps) to prevent env drift.
- Frontend vitest suites lint cleanly thanks to explicit Vitest globals and TS-safe blueprint definitions.

## [1.1.0] - 2025-11-15

### Added
- Search telemetry ingestion CLI (`workshop/scripts/search_telemetry.py`, with the archived `legacy/datalab/scripts/search_telemetry.py` kept for historical reference) plus the Papermill-tested notebook `workshop/notebooks/search_telemetry.ipynb` for Ops Deck hygiene trends.
- LabControl automation for telemetry refreshes (`-RunSearchTelemetryIngestion`) and full release pipelines (version bumps, changelog templating, tests, integrity, pushes).
- Changelog templating scaffold (`docs/CHANGELOG_TEMPLATE.md`) and new `ReleaseChangelogSection` flag for structured notes.

### Changed
- `Publish-LabRelease` now supports `-Bump` presets, changelog templates/sections, `Invoke-LabReleasePipeline`, and `Resolve-LabReleaseVersion` helper.
- `tests/test_notebooks.py` exercises the new telemetry notebook and parameterizes `SEARCH_LEDGER_PATH` for deterministic renders.

## [0.2.0] - 2025-11-15

### Added
- `docs/ELEMENTS_SPEC.md` describing the Elements widget + node system charter.
- Frontend Elements library scaffold (registry, presets, Zustand store, React Flow canvas, Storybook story, Vitest coverage).
- Control Center Elements panel surfacing the new workbench plus updated README + relay docs.

## [0.1.0] - 2025-11-15

### Added
- FastAPI `/api/control/*` endpoints, `NotebookRunner`, and accompanying pytest coverage.
- Control Center Relay React entrypoint (widgets, stories, Vitest suite, Storybook builds).
- `scripts/control_center.py` orchestration CLI with Papermill automation.
- Papermill notebook `control_center_relay.ipynb` plus smoke tests.
- GitHub Actions workflow "Full Test Suite" spanning backend, notebooks, frontend, and Storybook builds.

### Improved
- Docs covering Ops workflows (`docs/CONTROL_CENTER_RELAY.md`, README quick start, release checklist).
- Integrity tooling via `project_integrity.py` checkpoints and new Git pre-push hook guidance.
