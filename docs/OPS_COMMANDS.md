# Ops Command Patterns & Reusable Workflows

The lab ships with a rich set of automation helpers so you can bootstrap, monitor, and checkpoint the entire stack without re-learning bespoke scripts. This page captures the canonical command patterns that agents should reuse (or extend) instead of reinventing ad‑hoc commands.

## 1. PowerShell LabControl module (Windows-first)

Load the module once per PowerShell session and you get a full suite of cmdlets that wrap recurring workflows such as job orchestration, integrity snapshots, and workspace backups.

```powershell
Import-Module "$PSScriptRoot\scripts\powershell\LabControl.psm1" -Force
```

### 1.1 Job lifecycle recipes

| Goal | Command | Notes |
| --- | --- | --- |
| Start a service | `Start-LabJob -Name backend` | Auto-activates the project's `.venv` and applies env vars defined in the job definition. Use `-Force` to restart an already-running job. |
| Stop / force stop | `Stop-LabJob -Name frontend -Force` | Stops the background job registered under the `Lab:` prefix. |
| Restart a service | `Restart-LabJob -Name datalab` | Convenience wrapper for stop + start. |
| Start everything | `Start-AllLabJobs` | Spins up backend, frontend, and DataLab concurrently. |
| Show status | `Show-LabJobs` | Lists every `Lab:` job along with PowerShell job state and timestamps. |
| Capture logs | `Receive-LabJobOutput -Name backend -Keep` | Streams buffered stdout/stderr; `-Keep` preserves the buffer for future reads. |

**Tip:** For scripted diagnostics, pair `Get-LabJobSnapshot | ConvertTo-Json` with `Test-LabFolderSnapshot` (below) so Ops Deck can correlate runtime state with filesystem digests.

### 1.2 Filesystem & integrity snapshots

| Task | Command pattern | Why it matters |
| --- | --- | --- |
| Quick digest | `Get-LabFolderSnapshot -Group backend -SkipContentHash | Select-Object Group,FileCount` | Fast count/metadata sweep used during our tagging sprint. Add `| ConvertTo-Json` for machine archival. |
| Full hash capture | `Get-LabFolderSnapshot -Group scripts | Save-LabFolderSnapshot -Group scripts` | Includes SHA-256 per file; defaults to `data/integrity/<group>-timestamp.json`. |
| Persist snapshot to disk | `Save-LabFolderSnapshot -Group datalab -Destination data/integrity/datalab-latest.json` | Useful before risky refactors; outputs path to saved JSON for audit logs. |
| Validate against saved snapshot | `Test-LabFolderSnapshot -SnapshotPath data/integrity/datalab-latest.json` | Re-computes hashes and emits drift report; fails the pipeline early if the tree diverged. |

### 1.3 Workspace backups

| Scenario | Command | Output |
| --- | --- | --- |
| Ad-hoc zip backup | `Save-LabWorkspace -Include chatai,datalab,data,scripts` | Produces `backups/workspace-YYYYMMDD-HHMMSS.zip` by default. |
| Customized destination | `Save-LabWorkspace -Destination "D:\Snapshots\chatgpt\workspace.zip"` | Ensures backups survive agent resets by writing outside the repo. |

Follow up with `Test-LabFolderSnapshot` or `python scripts/project_integrity.py checkpoint ...` to record the backup’s hash lineage.

## 2. Cross-platform control via `labctl`

Linux/WSL hosts share the same mental model thanks to `scripts/labctl.sh`. Use it directly on Linux or through the PowerShell façade for Windows.

### 2.1 Native Linux / macOS usage

```bash
./scripts/labctl.sh start backend
./scripts/labctl.sh status --json | jq '.'
./scripts/labctl.sh backup ~/ChatAI-DataLab/backups/workspace.tar.gz
```

Key subcommands mirror the PowerShell cmdlets: `start`, `stop`, `restart`, `status`, `logs`, `backup`, `restore`, `install`, and `remote` (SSH passthrough for remote labs).

### 2.2 Windows-to-WSL handoff

```powershell
Invoke-LabUnixControl -Arguments @('status', '--json') -Shell Auto
```

- Automatically prefers WSL; falls back to Git Bash if WSL is unavailable.
- Accepts `-Distribution <distro>` when you need to pin to a specific WSL instance.
- Use `-PassThru` to capture the text output as an array (helpful for piping into `ConvertFrom-Json`).

## 3. Integrity CLI vs. LabControl snapshotting

Both the Python integrity CLI and the PowerShell snapshot helpers aim to record filesystem truth. Use them together:

1. `python scripts/project_integrity.py status --tags backend,ops` to confirm the repo is clean.
2. `Get-LabFolderSnapshot -Group backend -SkipContentHash` for a fast count, or omit `-SkipContentHash` before checkpointing.
3. `python scripts/project_integrity.py checkpoint --reason "backend patch" --tag backend` to write the authoritative manifest.

This pairing gives you quick iteration (PowerShell snapshot) plus tamper-proof manifests (Python CLI).

## 4. Ready-made command sequences

| Workflow | Steps |
| --- | --- |
| **Daily bring-up (Windows)** | `Import-Module scripts/powershell/LabControl.psm1` → `Start-AllLabJobs` → `Show-LabJobs` |
| **Tag sweep prep** | `Get-LabFolderSnapshot -Group scripts -SkipContentHash` → modify files → `Test-LabFolderSnapshot -SnapshotPath <latest snapshot>` |
| **Pre-release capture** | `Save-LabWorkspace` → `python scripts/project_integrity.py checkpoint --tag release --reason "v0.5.0"` → `./scripts/labctl.sh backup backups/release-v0.5.0.tar.gz` |
| **Remote lab action** | `./scripts/labctl.sh remote mylab.example.com ~/ChatAI-DataLab status --json` (native) or `Invoke-LabUnixControl -Arguments @('remote','mylab.example.com','status')` (PowerShell) |

## 5. Extending the toolkit

- New jobs: add entries to `Get-LabJobDefinitions` (PowerShell) **and** `register_job` blocks in `scripts/labctl.sh` so both shells stay aligned.
- Custom snapshots: wrap `Get-LabFolderSnapshot` in higher-level functions but keep the object shape `{ RelativePath, Length, Hash }` so downstream tooling keeps working.
- Document every new command sequence by appending to this file—future agents rely on it to rediscover operational muscle memory quickly.
