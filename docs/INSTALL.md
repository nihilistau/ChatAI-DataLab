# Installation & Environment Guide

This guide captures the reproducible bootstrap steps for every supported platform. All steps assume you cloned `ChatAI-DataLab` into your workspace root.

## 1. Prerequisites

| Platform | Requirements |
| --- | --- |
| Windows 11 | PowerShell 7+, WSL (optional), Python 3.10+, Node.js 18+, Git |
| macOS 13+ | Homebrew (recommended), Python 3.10+, Node.js 18+, Git |
| Linux (Debian/Ubuntu) | `apt` access, Python 3.10+, Node.js 18+, Git |
| Codespaces/Containers | Dev container with Python + Node toolchains |

> 📝 The repo never stores API keys. Create a `.env` at the repo root if you need to run against OpenAI or Cosmos DB.

## 2. Automated bootstrap

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

What the script does:

1. Detects package manager (`apt`, `pacman`) and installs Python, Node, and Git if missing.
2. Creates `.venv` folders for `playground/backend` and `kitchen`, upgrades `pip`, installs `requirements.txt` files.
3. Runs `npm install` + `npm run build` inside `playground/frontend`.
4. Prints next-step commands for backend/frontend/DataLab runners.

Re-running the script is safe; it refreshes dependencies and rebuilds the frontend bundle.

## 3. Platform-specific control planes

### Windows + PowerShell

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/lab-control.ps1 -ControlCenter
```

- Launches the Lab Control dashboard with buttons to start/stop backend, frontend, and Kitchen.
- Provides `Invoke-LabUnixControl` to bridge into WSL if you need Linux-specific orchestration.

### Linux / macOS / WSL

```bash
./scripts/labctl.sh status
./scripts/labctl.sh start-all
./scripts/labctl.sh logs backend
```

- Job metadata lives under `.labctl/state` and log streams under `.labctl/logs`.
- `labctl.sh backup <path>` creates tarball snapshots you can ship elsewhere.

## 4. Verifying the stack

1. **Backend health**: `curl http://localhost:8000/health` → `{ "status": "ok" }`.
2. **Frontend dev server**: visit `http://localhost:5173` and submit a prompt; you should see Tail Log entries for keystrokes and Ops Deck polls.
3. **Kitchen notebook**: `cd kitchen && . .venv/bin/activate && jupyter lab` then open `notebooks/hypothesis_control.ipynb` (the `legacy/datalab` tree is read-only for archival reference).
4. **Integrity baseline**: `python scripts/project_integrity.py status` should report `0 changed` right after a checkpoint.

## 5. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `uvicorn` cannot import `controlplane` | Run the backend from the repo root or set `PYTHONPATH` to `.` |
| Tail logs empty | Ensure `playground/backend` migrations ran (startup creates tables) and Ops Deck can reach `/api/tail-log` |
| `node-gyp` build failures | Install build tools (`xcode-select --install` on macOS, `build-essential` on Linux, VS Build Tools on Windows) |
| Notebook widgets missing | `pip install -r kitchen/requirements.txt` and restart the Jupyter kernel |

## 6. Next steps

- Read `docs/FILE_SYSTEM.md` to understand ownership and guardrails.
- Follow `docs/TUTORIALS.md` for an end-to-end instrumentation → insight dry run (all core features are implemented; future tutorials will cover new additions as they ship).
- Initialize the integrity manifest: `python scripts/project_integrity.py init --reason "post-setup"` (integrity tooling is fully implemented; future enhancements may expand automation or reporting).
