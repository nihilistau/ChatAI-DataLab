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

## 6. Search Toolkit & observability shortcuts

Repeatedly retyping ad-hoc `Get-ChildItem` + `Select-String` commands is error-prone, so the repo now includes a lightweight PowerShell module and preset catalog for common searches (TODO sweeps, "unimplemented" audits, doc scans, etc.). The module also emits structured logs so we can observe search activity over time.

### 6.1 Loading the module

```powershell
Import-Module "$PSScriptRoot\scripts\powershell\SearchToolkit.psm1" -Force
```

### 6.2 Single-shot searches

```powershell
# Literal match (default), scoped to Python + TS/JS/Markdown
Invoke-RepoSearch -Pattern "TODO" -FileProfile python,frontend,docs

# Regex search, include notebooks, keep vendor directories
Invoke-RepoSearch -Pattern "http(s)?://" -Regex -FileProfile notebooks -IncludeVenv -IncludeNodeModules

# Dry run to preview filters without executing Select-String
Invoke-RepoSearch -Preset repo-todos -DryRun
```

Key switches mimic CLI flags you might expect elsewhere:

| Switch | Effect |
| --- | --- |
| `-FileProfile` | Shortcut for curated extension sets defined in `scripts/powershell/search-presets.json` (`python`, `frontend`, `docs`, `notebooks`, `all`). |
| `-IncludeVenv`, `-IncludeNodeModules`, `-IncludeStorybook`, `-IncludeGit`, `-IncludePyCache` | Opt back into directories that are excluded by default. |
| `-Preset <name>` | Replays a saved preset (`repo-todos`, `docs-todos`, `backend-unimplemented`, or any new entries you add to the JSON). |
| `-EmitStats` | (On by default.) Prints a summary table with file counts, match counts, and runtime in milliseconds. |
| `-ListFiles` | Returns the candidate file set instead of running `Select-String`. |
| `-NoLog` | Skips observability logging for the run. |

### 6.3 Presets & history

- Presets live in `scripts/powershell/search-presets.json`. Each entry documents the include/exclude filters plus the original raw command that inspired it.
- Current catalog: `repo-todos`, `docs-todos`, `backend-unimplemented`, `frontend-debug-logs`, `backend-print-debug`, `security-http-links`, and `tests-skip-markers`. Keep naming descriptive so LabControl surfaces stay readable.
- Every invocation writes a JSON line into `logs/search-history.jsonl` (create the `logs` directory if it does not exist). Use `Get-SearchHistory -Last 10` to inspect recent runs or `Get-SearchHistory -Raw` for raw JSON.
- Extend the catalog by appending new objects to the `presets` array or by referencing the `extensionSets` shortcuts for language-specific searches.
- The `scripts/lab-control.ps1` entrypoint now proxies searches: e.g. `pwsh -File scripts/lab-control.ps1 -SearchPreset repo-todos -EmitStats`. This loads `LabControl.psm1`, which exposes `Invoke-LabSearch` and `Get-LabSearchPresets` for interactive shells.

This shared toolkit lets every agent grab a battle-tested command (`Invoke-RepoSearch`) instead of recreating bespoke `Select-String` pipelines, while the log stream adds the observability hook we were missing.

## 7. Release automation helper

- Use `Publish-LabRelease -Version 1.0.0 -DryRun` to see whether the repo is clean, the integrity check passes, and if a tag already exists.
- Add `-ReleasePush`/`-Push` to actually run `git push origin main` plus the annotated tag once the checks succeed.
- `-Force` overrides dirty working trees or existing tags (use sparingly), while `-SkipIntegrity` is available when `project_integrity.py status` is intentionally bypassed.
- The `scripts/lab-control.ps1` entrypoint surfaces the same functionality: `pwsh -File scripts/lab-control.ps1 -ReleaseVersion 1.0.0 -ReleaseDryRun`.
