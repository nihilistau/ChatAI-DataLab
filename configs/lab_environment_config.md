# Lab Environment Configuration Reference

_Last updated: 2025-11-15_

This document centralizes the canonical paths, syntax conventions, and escape rules that the automation tooling relies on. The new `scripts\lab-bootstrap.ps1` script exports each of these as global variables at runtime so PowerShell sessions, LabControl jobs, and CI scripts remain in sync.

## Global Path Variables

| Variable | Description | Windows Path |
| --- | --- | --- |
| `$global:LabRoot` | Monorepo root | `D:\Files\Code 3\ChatAI-DataLab` |
| `$global:LabScripts` | Cross-platform scripts directory | `D:\Files\Code 3\ChatAI-DataLab\scripts` |
| `$global:PShell` | PowerShell module directory | `D:\Files\Code 3\ChatAI-DataLab\scripts\powershell` |
| `$global:LabBackend` | FastAPI backend | `D:\Files\Code 3\ChatAI-DataLab\chatai\backend` |
| `$global:LabBackendEnv` | Backend virtual environment | `D:\Files\Code 3\ChatAI-DataLab\chatai\backend\.venv` |
| `$global:LabFrontend` | Vite/React frontend | `D:\Files\Code 3\ChatAI-DataLab\chatai\frontend` |
| `$global:LabFrontendEnv` | Node modules cache | `D:\Files\Code 3\ChatAI-DataLab\chatai\frontend\node_modules` |
| `$global:LabKitchen` | Notebook workspace | `D:\Files\Code 3\ChatAI-DataLab\kitchen` |
| `$global:LabKitchenEnv` | Kitchen virtual environment | `D:\Files\Code 3\ChatAI-DataLab\kitchen\.venv` |
| `$global:LabPyKernel` | Primary Python kernel executable | `D:\Files\Code 3\ChatAI-DataLab\kitchen\.venv\Scripts\python.exe` |
| `Env:LAB_ROOT` | Exported for Python/Node tooling (`kitchen.lab_paths`) | `D:\Files\Code 3\ChatAI-DataLab` |
| `Env:LAB_KITCHEN` | Workspace hint for CLI + Papermill jobs | `D:\Files\Code 3\ChatAI-DataLab\kitchen` |
| `Env:DATABASE_PROVIDER` | Active datastore provider consumed by backend/Kitchen/CLI | `sqlite` (default) or `json`/`cosmos` as configured |
| `Env:DATABASE_PATH` | File-backed datastore path when the provider requires one | `D:\Files\Code 3\ChatAI-DataLab\data\interactions.db` when `DATABASE_PROVIDER=sqlite`; otherwise `auto` |

> When `DATABASE_PATH=auto`, helpers such as `python scripts/playground_store.py summary` resolve the appropriate location (JSON snapshots, Cosmos endpoints, etc.) without additional configuration. Override the path only for intentional file-backed test runs.

These values are computed dynamically at runtime, so the same script works if the repo moves to a different drive letter—as long as the directory structure is preserved.

## Canonical Command Syntax

| Task | PowerShell Command | Notes |
| --- | --- | --- |
| Activate backend venv | `. "${global:LabBackendEnv}\Scripts\Activate.ps1"` | Use double quotes because the path contains spaces. Call `deactivate` when finished. |
| Activate Kitchen venv | `. "${global:LabKitchenEnv}\Scripts\Activate.ps1"` | Provides the `ipykernel` runtime for notebooks. |
| Start backend API | `Start-LabJob -Name backend -Force` | Requires `LabControl.psm1`. Automatically exports `PYTHONPATH`. |
| Start frontend dev server | `Start-LabJob -Name frontend -Force` | Uses the repo-local Node toolchain installed via `npm install`. |
| Start Kitchen Jupyter | `Start-LabJob -Name kitchen -Force` | Launches `jupyter lab --no-browser`. |
| Validate notebooks | `& $global:LabPyKernel scripts\tools\validate_notebooks.py` | The bootstrap script wraps this inside `Invoke-LabSyntaxScan`. |
| Compile backend sources | `& $global:LabPyKernel -m compileall chatai\backend` | Catches Python syntax errors before runtime. |

## Escape Character Quick Reference

- **PowerShell paths:** wrap any path containing spaces in double quotes and escape embedded quotes with the backtick (`` ` " ``). Example: `. "D:\Files\Code 3\ChatAI-DataLab\chatai\backend\.venv\Scripts\Activate.ps1"`.
- **PowerShell literals:** use backtick (`` ` ``) to escape special characters (e.g., `` `n`` for newline). Prefer single quotes when no interpolation is required.
- **JSON/TS configs:** escape backslashes as `\\` inside strings (e.g., `"D\\Files\\Code 3\\ChatAI-DataLab\\data\\store.sqlite"`). When a config needs to surface the datastore (such as `VITE_DEFAULT_DB_PATH`), source the value from `DATABASE_PATH` instead of hardcoding `interactions.db` so provider swaps stay painless.
- **Bash/WSL commands:** wrap Windows-style paths with single quotes and convert backslashes to forward slashes when possible (e.g., `'D:/Files/Code 3/ChatAI-DataLab/scripts/labctl.sh'`).

## Validation & Location Checks

Run the bootstrap scan to ensure notebooks, backend Python modules, frontend configs, and Lab scripts are in the expected locations and free of structural issues:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\lab-bootstrap.ps1
```

The scan performs the following:

1. Parses every notebook under `kitchen/notebooks` (plus the archived `legacy/datalab` copies for historical reference) as JSON to catch malformed cells.
2. Runs `compileall` against `playground/backend`, `kitchen/scripts`, and shared utility modules to surface Python syntax errors early.
3. Confirms that `package.json`, `tsconfig.json`, and `vite.config.ts` are loadable JSON/TypeScript config files with valid escape sequences.
4. Verifies that all global paths listed above exist before LabControl starts any jobs.

Refer back to this document whenever you need to confirm quoting rules, directory aliases, or executable paths shared between Windows PowerShell, WSL, and notebook kernels.

## Diagnostics & Health Checks

- **Structured log**: All LabControl events, notebook snapshots, and health probes append JSONL records to `data/logs/lab-diagnostics.jsonl`. The folder is created on demand and ignored by git (see `.gitkeep`).
- **Python probe**: `scripts/control_health.py` verifies the Control API, SQLite connectivity, and `LAB_ROOT` alignment. Run it manually or via `Test-LabHealth` inside LabControl.
- **LabControl command**: `Test-LabHealth -StatusUrl http://localhost:8000/api/control/status` streams the Python output, logs to `lab-diagnostics.jsonl`, and raises if the stack is degraded.
- **Notebook metadata**: Every Papermill run now writes `_papermill/run_metadata.json` so Ops tooling can audit which DB path and env produced a snapshot.
