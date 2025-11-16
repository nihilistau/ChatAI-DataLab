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
| `$global:LabDatalab` | Notebook workspace | `D:\Files\Code 3\ChatAI-DataLab\datalab` |
| `$global:LabDatalabEnv` | DataLab virtual environment | `D:\Files\Code 3\ChatAI-DataLab\datalab\.venv` |
| `$global:LabPyKernel` | Primary Python kernel executable | `D:\Files\Code 3\ChatAI-DataLab\datalab\.venv\Scripts\python.exe` |
| `Env:LAB_ROOT` | Exported for Python/Node tooling (`datalab.lab_paths`) | `D:\Files\Code 3\ChatAI-DataLab` |

These values are computed dynamically at runtime, so the same script works if the repo moves to a different drive letter—as long as the directory structure is preserved.

## Canonical Command Syntax

| Task | PowerShell Command | Notes |
| --- | --- | --- |
| Activate backend venv | `. "${global:LabBackendEnv}\Scripts\Activate.ps1"` | Use double quotes because the path contains spaces. Call `deactivate` when finished. |
| Activate DataLab venv | `. "${global:LabDatalabEnv}\Scripts\Activate.ps1"` | Provides the `ipykernel` runtime for notebooks. |
| Start backend API | `Start-LabJob -Name backend -Force` | Requires `LabControl.psm1`. Automatically exports `PYTHONPATH`. |
| Start frontend dev server | `Start-LabJob -Name frontend -Force` | Uses the repo-local Node toolchain installed via `npm install`. |
| Start DataLab Jupyter | `Start-LabJob -Name datalab -Force` | Launches `jupyter lab --no-browser`. |
| Validate notebooks | `& $global:LabPyKernel scripts\tools\validate_notebooks.py` | The bootstrap script wraps this inside `Invoke-LabSyntaxScan`. |
| Compile backend sources | `& $global:LabPyKernel -m compileall chatai\backend` | Catches Python syntax errors before runtime. |

## Escape Character Quick Reference

- **PowerShell paths:** wrap any path containing spaces in double quotes and escape embedded quotes with the backtick (`` ` " ``). Example: `. "D:\Files\Code 3\ChatAI-DataLab\chatai\backend\.venv\Scripts\Activate.ps1"`.
- **PowerShell literals:** use backtick (`` ` ``) to escape special characters (e.g., `` `n`` for newline). Prefer single quotes when no interpolation is required.
- **JSON/TS configs:** escape backslashes as `\\` inside strings (e.g., `"data\\interactions.db"`).
- **Bash/WSL commands:** wrap Windows-style paths with single quotes and convert backslashes to forward slashes when possible (e.g., `'D:/Files/Code 3/ChatAI-DataLab/scripts/labctl.sh'`).

## Validation & Location Checks

Run the bootstrap scan to ensure notebooks, backend Python modules, frontend configs, and Lab scripts are in the expected locations and free of structural issues:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\lab-bootstrap.ps1
```

The scan performs the following:

1. Parses every notebook under `datalab/notebooks` as JSON to catch malformed cells.
2. Runs `compileall` against `chatai/backend` and `datalab/scripts` to surface Python syntax errors early.
3. Confirms that `package.json`, `tsconfig.json`, and `vite.config.ts` are loadable JSON/TypeScript config files with valid escape sequences.
4. Verifies that all global paths listed above exist before LabControl starts any jobs.

Refer back to this document whenever you need to confirm quoting rules, directory aliases, or executable paths shared between Windows PowerShell, WSL, and notebook kernels.

## Diagnostics & Health Checks

- **Structured log**: All LabControl events, notebook snapshots, and health probes append JSONL records to `data/logs/lab-diagnostics.jsonl`. The folder is created on demand and ignored by git (see `.gitkeep`).
- **Python probe**: `scripts/control_health.py` verifies the Control API, SQLite connectivity, and `LAB_ROOT` alignment. Run it manually or via `Test-LabHealth` inside LabControl.
- **LabControl command**: `Test-LabHealth -StatusUrl http://localhost:8000/api/control/status` streams the Python output, logs to `lab-diagnostics.jsonl`, and raises if the stack is degraded.
- **Notebook metadata**: Every Papermill run now writes `_papermill/run_metadata.json` so Ops tooling can audit which DB path and env produced a snapshot.
