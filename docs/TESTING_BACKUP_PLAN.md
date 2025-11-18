# Testing & Backup Strategy

A resilient lab requires two safety nets: repeatable automated tests and dependable backups. This plan defines what to run, when to run it, and which built-in tools to lean on so the system stays trustworthy even as the codebase evolves.

## 1. Testing Strategy

| Layer | Scope | Tooling | Command | Cadence |
| --- | --- | --- | --- | --- |
| Backend unit/integration tests | FastAPI routes, schemas, services under `playground/backend` | `pytest` (already in `requirements.txt`) | ```pwsh
cd playground/backend
python -m pytest -q
``` | Run locally before pushing and on every PR (CI). |
| Backend contracts | 1) Request/response shapes vs. frontend expectations 2) DB migrations | `pytest -m contract` (add marker) + schema diff via Alembic (future) | Define fixtures in `playground/backend/tests/conftest.py` to load canned payloads and assert response JSON. | Nightly or before releasing. |
| Backend quality gates | Import errors, type hints, formatting | `python -m compileall playground/backend`, `ruff check` once added to toolchain | Add to CI once linting config lands. | CI + pre-commit. |
| Frontend smoke tests | Rendering of critical React components, API client stubs | `vitest` / `npm test -- --runInBand` (once suite added) | Seed with snapshots for `CanvasBoard`, `TailLogCell`, etc. Run commands from `playground/frontend`. | Before merging UI changes. |
| Frontend e2e (stretch) | Chat flow from prompt to response | Playwright or Cypress pointing to local FastAPI | `npx playwright test --project=chromium` | Nightly or release candidate. |
| Kitchen validations | Notebook helpers (`kitchen/scripts/*.py`), metrics sanity checks | `pytest kitchen/scripts` + `papermill` smoke for key recipes | ```pwsh
cd kitchen
python -m pytest scripts
papermill notebooks/quickstart.ipynb /tmp/quickstart-smoke.ipynb
``` | Weekly or before publishing research findings. |
| Ops tooling | PowerShell + Bash orchestration scripts | `pwsh -File scripts/powershell/test-import.ps1`, `./scripts/labctl.sh status` under CI | Ensures LabControl module loads and job definitions stay in sync. | On every CI run touching `scripts/`. |

### 1.1 Test data management

- Use the datastore fixture in `playground/backend/tests/conftest.py` (in-memory SQLite) to keep unit tests isolated while still exercising `data_store_context`.
- When a test needs to touch a file-backed store, point `DATABASE_PATH` (and optionally `DATABASE_PROVIDER=sqlite`) to a temporary directory before invoking pytest. Example:
	```powershell
	$env:DATABASE_PROVIDER = "sqlite"
	$env:DATABASE_PATH = (Resolve-Path (New-Item -ItemType File -Path .\tests\tmp\interactions-test.db)).Path
	python -m pytest -m "db"
	```
	This keeps the repo’s `data/` tree untouched while still validating migrations/IO paths.
- Capture anonymized golden payloads (JSON) under `playground/backend/tests/data/` so the same request corpus powers regression tests, Kitchen recipes, and API documentation.

### 1.2 Automation roadmap

**Automation roadmap (current state and future additions):**
1. GitHub Actions workflow (`.github/workflows/test.yml`) is implemented and runs backend `pytest`, PowerShell import tests, and `labctl` status checks in Ubuntu + Windows runners.
2. Linting tools (`ruff` for backend, `eslint`/`tsc --noEmit` for frontend) are partially implemented; further integration may be added to catch drift before runtime.
3. Integrity checks (`python scripts/project_integrity.py status --tags backend,ui`) are available and can be wired into CI for additional protection against accidental file deletions. Future enhancements may expand coverage or automation.

## 2. Backup Strategy

Multiple built-in tools already cover snapshotting; this section standardizes how and when to use them.

### 2.1 Routine workspace archives

| Situation | Command | Storage target |
| --- | --- | --- |
| Daily developer snapshot (Windows) | `Save-LabWorkspace` | `backups/workspace-YYYYMMDD-HHMMSS.zip` (local). |
| Daily developer snapshot (Linux/WSL) | `./scripts/labctl.sh backup ~/ChatAI-DataLab/backups/workspace.tar.gz` | `~/ChatAI-DataLab/backups`. |
| Pre-release artifact | `Save-LabWorkspace -Destination "../releases/playground-kitchen-v0.5.0.zip"` | Checked-in `releases/` dir or external blob storage. |

**Policy**: keep the last 7 dailies locally; upload weekly releases to remote storage (Azure Blob, S3, etc.) with a retention of ≥90 days.

### 2.2 Integrity checkpoints (fine-grained)

1. Confirm working tree cleanliness: `python scripts/project_integrity.py status`.
2. Create a checkpoint with context: `python scripts/project_integrity.py checkpoint --tag backend --reason "refactor chat routes"`.
3. Store the JSON + file copies under `.project_integrity/checkpoints/<stamp>`; optionally export with `... export backups/backend-refactor.zip` for offsite archival.

Use checkpoints:
- Before migrations/data model changes.
- After tag sweeps or tooling upgrades.
- Prior to merging long-lived feature branches.

### 2.3 Kitchen artifacts

- Save recipes (notebooks) with embedded outputs into `kitchen/notebooks/exports/` and commit only sanitized versions (PII scrubbed).
- Use `papermill` or `nbconvert` to render HTML/PDF snapshots and upload alongside workspace archives.
- When recipes depend on large intermediate files, stash them in `data/artifacts/<date>/` and include that folder in `Save-LabWorkspace -Include playground,kitchen,data,scripts` (already default).

### 2.4 Restore drills

| Drill | Frequency | Steps |
| --- | --- | --- |
| Verify zip integrity | Monthly | `pwsh -Command "Expand-Archive backups/workspace-2025-11-01.zip -DestinationPath tmp/restore"` then run `python scripts/project_integrity.py status --manifest tmp/restore/.project_integrity/index.json`. |
| Simulated host loss | Quarterly | Stand up a clean VM, run `git clone` + `./scripts/setup.sh`, restore latest workspace archive, run smoke tests (`pytest`, `npm run build`, `papermill`). |

### 2.5 Ownership & logging

- Record every backup/checkpoint in `data/ops-log.md` (create if missing) with `{timestamp, operator, command, destination}` so Ops Deck can display lineage.
- Configure future CI pipelines to upload `Save-LabWorkspace` artifacts as build outputs (GitHub Actions artifacts, Azure Storage, etc.).

## 3. Immediate next steps

1. Add GitHub Actions workflow to run backend `pytest`, PowerShell import tests, and `labctl` status checks.
2. Create a scheduled job (`cron`) on the primary dev machine (or CI) that runs `Save-LabWorkspace` nightly and syncs the zip to cloud storage.
3. Pilot a restore drill using the current backups to validate the instructions above.

Document updates should accompany any new automation: append new commands to `docs/OPS_COMMANDS.md` and refresh this plan whenever tooling changes.
