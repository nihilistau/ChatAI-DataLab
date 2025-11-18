# Release Checklist

Use this checklist any time you prepare an internal drop or GitHub release. It codifies the automation already wired into CI plus the integrity tooling that ships with the repo.

## 1. Update metadata

- [ ] Review `CHANGELOG.md` and add an entry that captures user-facing changes.
- [ ] Run `python scripts/project_integrity.py status --baseline <last-tag>` to see the exact delta versus the previous release checkpoint. (Pass either a checkpoint id such as `0002` or a git tag like `v1.0.1-stability.20251116`.)
- [ ] If new assets or configs were added, run `python scripts/project_integrity.py checkpoint --tag release --reason "vX.Y.Z"` to snapshot them.

## 2. Verify automation locally

```bash
# Backend
python -m pip install -r playground/backend/requirements.txt
python -m pytest playground/backend/tests -q

# Telemetry + notebooks
python -m pip install -r kitchen/requirements.txt  # full Kitchen notebook deps
python -m scripts.search_telemetry ingest --log-path logs/search-history.jsonl --output data/search_telemetry.json \
	--runs-parquet data/search_telemetry-runs.parquet --daily-parquet data/search_telemetry-daily.parquet
python -m papermill kitchen/notebooks/search_telemetry.ipynb kitchen/notebooks/_papermill/search_telemetry-release.ipynb \
	-p SEARCH_LEDGER_PATH data/search_telemetry.json \
	-p TELEMETRY_LOG_PATH logs/search-history.jsonl
python -m pytest tests/test_notebooks.py -q

# Frontend
cd playground/frontend
npm install
npm run lint
npm run test
npm run test:playground
npm run build
npm run storybook:build
npm run storybook:playground
```

> `scripts/release_checklist.ps1` runs the telemetry ingest + Papermill snapshot automatically. Pass `-SkipTelemetry` when you need to bypass it temporarily (for example, when log files are unavailable).

## 3. Collect artifacts

- [ ] Zip and attach `playground/frontend/dist/` (`control-center-dist.zip`).
- [ ] Zip and attach `playground/frontend/storybook-static/` and `playground/frontend/storybook-static-playground/` (`storybook-static.zip`, `storybook-static-playground.zip`).
- [ ] Copy the freshly executed notebooks from `kitchen/notebooks/_papermill/` (Search Telemetry, Ops Response Playbook, Widget Showcase) and link them in the release body.
- [ ] Mention the operator scripts added or updated in this release (`scripts/lab-bootstrap.ps1`, `scripts/release_checklist.ps1`, `scripts/lab-control.ps1`, etc.) so downstream users know which automation changed.
- [ ] Capture screenshots/GIFs of the Playground UI or Storybook stories if visual changes were made.

## 4. Git + GitHub hygiene

- [ ] Ensure the `scripts/git-hooks/pre-push.sh` hook is installed locally (`cp scripts/git-hooks/pre-push.sh .git/hooks/pre-push`).
- [ ] Rebase against `origin/main` and rerun the Full Test Suite if the diff is non-trivial.
- [ ] Tag the release with `git tag -a vX.Y.Z -m "Release notes"` and push via `git push origin main --tags`.

Example for Framework v1.0.0:

```bash
git checkout main
git pull --ff-only
python scripts/project_integrity.py status
git status
git tag -a v1.0.0 -m "Framework v1.0.0"
git push origin main
git push origin v1.0.0
```

Equivalent PowerShell shortcut:

```powershell
pwsh -File scripts/lab-control.ps1 -ReleaseBump patch -ReleasePipeline -ReleaseDryRun
pwsh -File scripts/lab-control.ps1 -ReleaseBump minor -ReleasePipeline -ReleaseChangelogTemplate docs/CHANGELOG_TEMPLATE.md -ReleaseChangelogSection Highlights -ReleaseChangelogSection Ops -ReleaseAsJob
```

Flags:

- `-ReleaseBump patch|minor|major` derives the next semantic version from Git tags; pass `-ReleaseVersion` when you need an explicit value instead.
- `-FinalizeChangelog` (or `-ReleaseChangelogTemplate docs/CHANGELOG_TEMPLATE.md -ReleaseChangelogSection ...`) inserts a templated entry at the top of `CHANGELOG.md`, replacing `{{VERSION}}` / `{{DATE}}` tokens automatically.
- `-RunTests` executes `scripts/release_checklist.ps1`, which runs backend tests, notebook tests, and the frontend lint/test/build suite (use `scripts/release_checklist.ps1 -Skip*` switches to trim scope).
- `-UpdateIntegrity` writes a new checkpoint via `project_integrity.py checkpoint --tag release` after the tests succeed.
- `-ReleasePipeline` wraps all helpers (tests, changelog, integrity, push) and can run as a background PowerShell job via `-ReleaseAsJob`. Combine it with `-ReleaseSkipChangelog`, `-ReleaseSkipTests`, or `-ReleaseSkipPush` for dry runs.

## 5. Publish

- [ ] Draft a GitHub release pointing at the new tag. Paste the `CHANGELOG` entry plus any notebook artifacts or screenshots.
- [ ] In the release body, explicitly link the Search Telemetry, Ops Response Playbook, and Widget Showcase notebooks along with the `LabControl` helper scripts installers so operators can replay evidence.
- [ ] Mark the release as "Latest" once CI passes.

Following these steps keeps GitHub releases reproducible and aligned with the automation wired into this repository.
