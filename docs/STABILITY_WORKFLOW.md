# Stability Workflow Playbook

_Updated: 2025-11-16_

This playbook freezes feature work and enforces a habitually tested stabilization cycle for ChatAI · DataLab. It coordinates
local habits, CI jobs, GitHub milestones, and release tagging so that every change tightens the existing system and surfaces
bugs quickly.

## 1. Principles

1. **Freeze first** — Only merge fixes, refactors, or documentation that reduce risk. New features must wait for the next
   unlocking memo recorded in `docs/GOALS_AND_ACHIEVEMENTS.md`.
2. **Test before touch** — Every pull request must include evidence of the full regression suite (backend, DataLab, frontend,
   notebooks, Storybook, integrity). Failing jobs block merges; do not force push over red builds.
3. **Source of truth is GitHub** — All work items live as GitHub issues tied to a `stability-week-YYYYWW` milestone. `main`
   always reflects the latest passing build.
4. **Automate drift detection** — The integrity toolkit (`scripts/project_integrity.py`) and Search Toolkit sweeps must run at
   least once per milestone. Record checkpoint IDs in release notes.
5. **Tag everything** — Each merge to `main` that changes runtime behavior increments a SemVer PATCH version and creates a tag
   plus checkpoint. This keeps the repo recoverable even during rapid bug fixing.

## 2. Branch + Issue Flow

| Step | Description |
| --- | --- |
| 1 | File an issue labelled `type:bug` or `type:hardening` and assign it to the current `stability-week-YYYYWW` milestone. |
| 2 | Create a branch named `stability/<issue-id>-slug` from `main`. No long-lived feature branches. |
| 3 | Link the branch + PR back to the issue (GitHub keywords) and include the enforced commit syntax (see `syntax.md`). |
| 4 | Keep branches rebased (no merge commits) and delete them immediately after merge. |
| 5 | Milestone burndown reviewed every Friday via GitHub milestones page + `docs/GOALS_AND_ACHIEVEMENTS.md`. |

## 3. Testing & Job Regime

### Local sequence (run before every push)

1. `python -m pytest -q` inside `chatai/backend`
2. `python -m pytest datalab/tests -q`
3. `python -m pytest tests/test_notebooks.py -q`
4. `npm run lint && npm run test && npm run build` inside `chatai/frontend`
5. `npm run storybook:build` and `npm run storybook:playground`
6. `python scripts/project_integrity.py status` (expect zero modified files outside the branch scope)

Use `scripts/lab-control.ps1` / `scripts/labctl.sh` helpers to start services if interactive validation is required.

### Continuous Integration (GitHub Actions)

`stability-gate` (see `.github/workflows/datalab-notebooks.yml`) fans out into discrete jobs:

- **backend-tests** — Python 3.11, installs `chatai/backend/requirements.txt`, runs `pytest -q`.
- **datalab-tests** — Python 3.11, installs `datalab/requirements.txt`, runs both `pytest datalab/tests -q` and
  `pytest tests/test_notebooks.py -q` to execute Papermill notebooks.
- **frontend-qa** — Node 20, `npm ci`, runs `lint`, `test`, `test:playground`, and `build`.
- **storybook-builds** — Node 20, builds Storybook + Control Center Storybook for regression screenshots.
- **integrity-scan** — Python 3.11, runs `python scripts/project_integrity.py status` and uploads summaries as artifacts.

Jobs must all be green before merging. The workflow also uploads executed notebooks for later inspection.

### Scheduled sweeps

Add a scheduled workflow (cron Sunday 02:00 UTC) that runs the same suite plus the Search Toolkit sweeps (`scripts/powershell/SearchToolkit.psm1` or
`./scripts/labctl.sh search-sweep`) to catch flaky tests and stale TODOs.

## 4. Versioning, Tags, and Milestone Commits

1. **Version bump** — Use SemVer patch increments while frozen (`v1.0.1`, `v1.0.2`, …). Update `CHANGELOG.md` using
   `docs/CHANGELOG_TEMPLATE.md` and run `Publish-LabRelease -Bump patch -DryRun` for validation.
2. **Tagging** — After merging to `main`, create annotated tags named `v<major>.<minor>.<patch>-stability.<YYYYMMDD>` and push
   tags to origin. Record the Git commit + tag in `docs/GOALS_AND_ACHIEVEMENTS.md`.
3. **Checkpoint** — Immediately run `python scripts/project_integrity.py checkpoint --tag <tag> --reason "release"` to persist
   `.project_integrity/checkpoints/<id>.json` and zipped backups.
4. **Milestone close** — Close the GitHub milestone once all issues are merged and a release tag exists. Start the next week’s
   milestone before reopening feature work.

## 5. Bug Discovery + Reporting

- **Search Toolkit** — Run `Search-LabRepo -Preset bug-hunt` (documented in `scripts/powershell/SearchToolkit.psm1`) daily to
  scan for suspicious patterns (error logs, TODOs). Log outputs to `logs/search-history.jsonl`.
- **Lab Diagnostics** — Execute `python datalab/diagnostics.py --quick` before shipping each fix to ensure environment health.
- **Notebook parity** — All new diagnostics get mirrored in `datalab/notebooks/control_center_playground.ipynb` with Papermill
  outputs committed to `datalab/notebooks/_papermill` for reproducibility.

## 6. GitHub Sync Checklist

1. Confirm issue is labelled, assigned, and includes acceptance criteria.
2. Ensure PR description links to issue and lists test evidence + command output URLs (artifact links).
3. Use the format specified in `syntax.md` for commits, pull request titles, tags, and milestone names.
4. After merge:
   - `git switch main && git pull`
   - `Publish-LabRelease -ReleasePipeline`
   - `git push --tags`
   - Update `docs/GOALS_AND_ACHIEVEMENTS.md` with a dated entry.

## 7. Backlog + Unlock Procedure

To end the freeze:

1. Draft a proposal describing the new feature scope and the defects fixed during the freeze.
2. Secure sign-off in the GitHub discussion thread linked to the upcoming milestone.
3. Record the decision in `PROJECT_OVERVIEW.md` under “Expanded Functionality” with the date + reference.
4. Update `syntax.md` if the unlock changes commit/tag semantics.

Until those steps land, treat this playbook as the governing process.```}