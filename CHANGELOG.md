# Changelog

All notable changes to this repository will be documented in this file. The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the repo follows semantic versioning.

## [0.2.0] - 2025-11-15

### Added
- `docs/ELEMENTS_SPEC.md` describing the Elements widget + node system charter.
- Frontend Elements library scaffold (registry, presets, Zustand store, React Flow canvas, Storybook story, Vitest coverage).
- Control Center Elements panel surfacing the new workbench plus updated README + playground docs.

## [0.1.0] - 2025-11-15

### Added
- FastAPI `/api/control/*` endpoints, `NotebookRunner`, and accompanying pytest coverage.
- Control Center Playground React entrypoint (widgets, stories, Vitest suite, Storybook builds).
- `scripts/control_center.py` orchestration CLI with Papermill automation.
- Papermill notebook `control_center_playground.ipynb` plus smoke tests.
- GitHub Actions workflow "Full Test Suite" spanning backend, notebooks, frontend, and Storybook builds.

### Improved
- Docs covering Ops workflows (`docs/CONTROL_CENTER_PLAYGROUND.md`, README quick start, release checklist).
- Integrity tooling via `project_integrity.py` checkpoints and new Git pre-push hook guidance.
