# Agent Operations Playbook

This playbook captures the high-trust patterns, scripts, and MCP entry points that keep Horizon Relay Platform agents effective across frontend, backend, and Workshop workflows.

## 1. Quick-start scripts

| Task | Command | Notes |
| --- | --- | --- |
| Launch Control Center relay | `npm run relay:dev` (from `relay/frontend`) | Uses the `ManifestProvider` hydrator and opens `control-center.html`. Ensure `.env` contains `VITE_RELAY_TENANT` and `VITE_RELAY_NAME`. |
| Run Ops orchestrator helpers | `python scripts/control_center.py <command>` | Supports `start`, `stop`, `status`, `notebook`, `elements`. Emits telemetry to `data/logs`. |
| Relay diagnostics | `python scripts/capsule_status.py --relay control` | Mirrors the Relay Health panel output until the script itself is renamed. |
| Notebook snapshot (Papermill) | `python scripts/control_center.py notebook --db-path auto --status-url http://localhost:8000/api/control/status` | Executes `workshop/notebooks/control_center_relay.ipynb` with provider-aware datastore wiring; outputs land in `workshop/notebooks/_papermill`. Keep `--db-path auto` unless replaying historical SQLite runs. |
| Inspect datastore provider | `python scripts/relay_store.py summary` | Reveals the active provider (SQLite/JSON/Cosmos) plus sample counts for interactions/artifacts/tail log. Pair with `interactions`, `artifacts`, `tail-log`, and `tail-log-add` subcommands for deeper inspection. |
| Control Center TUI | `python scripts/tui/control_center_tui.py --auto-refresh 10` | Lightweight Textual dashboard that streams release + tail logs with the same telemetry hooks as other CLIs. |
| Freeze → tag pipeline | `python scripts/release_pipeline.py [options]` | Fully automated freeze → tests → checkpoint → tag/push flow. Supports `--dry-run`, `--allow-dirty`, `--skip-integrity`, `--force-release-dir`, `--no-push`, `--no-auto-fix`, and `--notes "context"` to embed commentary. Emits a tail log entry via `scripts/relay_store.py tail-log-add` (override with `--tail-log-source` / `--tail-log-message`, disable with `--skip-tail-log`) and appends to `data/logs/release.log` unless `--skip-release-log` is supplied. |
| Ops workflow harness | `python scripts/workflow_harness.py [options]` | Chains release dry-run, goals log entry, change record creation, rebrand dry-run, and an integrity checkpoint/status snapshot. Emits a tail log entry (`scripts/relay_store.py tail-log-add`) plus a release log record (`data/logs/release.log`) unless `--skip-tail-log`/`--skip-release-log` is provided. Use `--timeline-json data/logs/workflow_harness/latest.json --timeline-jsonl data/logs/workflow_harness/history.jsonl` to capture machine-readable summaries. Also available via `python scripts/control_center.py workflow -- <args>`. |
| Change history system | `python scripts/change_runs.py list` / `show <id>` / `new --title ...` | Optional, agent-populated reports under `/changes`. Use when a user wants a narrative; it never replaces Git/release guardrails. |
| Rapid rebrand automation | `python scripts/rebrand_reset.py --config configs/rebrand_plan.example.json --dry-run` | Dry-run prints the rename/replacement/validation plan; drop `--dry-run` to execute. Customize the JSON to swap tokens, rename directories, copy notebooks, and run validations in one pass. |
| Rebrand via control_center | `python scripts/control_center.py rebrand --dry-run` | CLI façade over `rebrand_reset`. Pass `--steps` or `--config` to tailor a run; omit `--dry-run` to execute. Mirrors the Control Center command palette entries. |
| Release log (headless) | `python scripts/release_log_cli.py --limit 10 --show-timeline` | Filter + page through `data/logs/release.log` without opening the file. Add `--json` for MCP automation or `--status failed` to zero in on broken runs. |

### Telemetry spans + release log emission

- `scripts/ops_telemetry.py` is the shared helper that every CLI should import when it needs tail-log or release-log coverage. Use the `telemetry_span()` context manager to:
   - emit a tail log entry when the span opens (unless `--skip-tail-log` is passed),
   - append structured release log rows with `summary`, `details`, `status`, and `timeline` metadata, and
   - capture `record_step()` calls so UI timelines stay in sync with headless runs.
- `python scripts/control_center.py ...` now wires every subcommand through telemetry spans. Global flags:
   - `--tail-log-source` / `--release-log-kind` let you tag the emitting component.
   - `--skip-tail-log` / `--skip-release-log` opt out when you truly need a silent run.
- `scripts/rebrand_reset.py` and `scripts/manifest_validator.py` expose the same telemetry flags, so dry-runs, apply runs, and manifest linting all land in both the tail log and `data/logs/release.log` automatically.
- New telemetry coverage includes `scripts/project_integrity.py`, `scripts/relay_store.py`, `scripts/change_runs.py`, `scripts/datastore_lint.py`, `scripts/capsule_status.py`, and the `scripts/tui/control_center_tui.py` monitor. Each CLI now forwards `--skip-tail-log`, `--skip-release-log`, `--tail-log-source`, `--release-log-kind`, and `--release-log-path` so Ops can trace any automation run uniformly.
- When you create new automation, wrap it with `telemetry_span(action="<verb>", component="<script>")` and reuse the same CLI flags so operators can rely on consistent observability toggles.

> **Path helpers live only in Workshop.** Import `data_path`, `lab_path`, `logs_path`, and `get_lab_root` from `workshop.lab_paths`. The legacy DataLab modules remain archived under `legacy/datalab` for historical reference only.

> **Diagnostics + widgets are Workshop-centric.** Use `workshop.diagnostics` for logging helpers (`append_diagnostic_record`, `record_run_metadata`, etc.) and `workshop.widgets` for `WidgetSpec`, `WidgetLibrary`, and catalog builders.

> **Manifest schema + validator live under Workshop.** Import `RelayManifest*` models and `validate_manifest_payload` from `workshop.manifests` (or `workshop.manifests.validator`).

> **Datastore CLI is the single source of truth.** `scripts/relay_store.py` talks to the same store the backend uses, regardless of provider. Prefer these subcommands over ad-hoc `sqlite3` sessions and log every manual mutation via `tail-log-add` so Ops can trace the change.

## 2. Manifest-aware UI development

1. Wrap any manifest-consuming UI in `<ManifestProvider>` (already wired in `src/main.tsx`).
2. Use the `useManifest()` hook for data, refresh, auto-refresh toggle, and timestamps.
3. When adding a new panel:
   - Show loading, empty, and error states.
   - Log revisions (`manifest · {relay} rev {revision} synced`).
   - Keep data display defensive (guard against missing metadata, sections, widgets, actions).
4. Record the change in `README.md` and Storybook if it affects design reviewers.

## 3. MCP + automation hooks

- **Notebook runners:** All Workshop notebooks surfaced via `scripts/control_center.py notebook <name>` automatically log to `data/logs/lab-diagnostics.jsonl`. Extend this script when adding new automation relays so other agents inherit the telemetry.
- **Manifest ops:** Prefer using the `ManifestPublisher` helper under `workshop/scripts/manifest.py` so checksum + revision logic stays centralized. (Wrap it in MCP or CLI glue when sharing with others.)
- **Manifest validator MCP command:** The Control Center seeds `data/commands.json` with a `Manifest validator (onboarding)` entry tagged `manifest/mcp/validator`. Run it from the Ops Deck command list or via `GET /api/commands?tag=manifest` + `POST /api/commands/{id}/run` to emit the JSON summary from `scripts/manifest_validator.py` without reaching for a shell.
- **Workflow harness command:** `Ops workflow harness` in `data/commands.json` wraps `python scripts/workflow_harness.py` (defaults to dry-run release + doc updates). Use it when a user requests the “release → docs → change record → rebrand” combo without juggling multiple CLIs. Pass the timeline flags (`--timeline-json`, `--timeline-jsonl`) so Ops Deck + MCP surfaces can ingest the structured results, and keep the default tail-log/release-log hooks unless you explicitly opt out via `--skip-tail-log` / `--skip-release-log`.
- **Rebrand workflow MCP commands:** Two new entries (`Rebrand · dry run`, `Rebrand · apply plan`) wrap `scripts/rebrand_reset.py` so agents can preview or execute rename plans entirely from the Ops Deck.
- **Datastore + tail logs:** CLI workflows that ingest telemetry or mutate artifacts should rely on `python scripts/relay_store.py ...`. Announce significant actions (ingest, migration, Papermill runs, manifest publish) with `python scripts/relay_store.py tail-log-add "<event>" --source <actor>` so the Control Center tail log mirrors automation.
- **Custom MCP tools:** When you register a new tool, capture its command, inputs, and outputs in this file. Include a short example invocation for future agents.

## 4. Validation checklist

Before landing changes:

1. **Frontend:**
   ```bash
   npm run check
   npm run build # optional but recommended before releases
   ```
2. **Backend / Workshop:**
   ```bash
   pytest
   python scripts/project_integrity.py
   ```
3. **Docs:** Update relevant markdown (README, OPERATIONS_HANDBOOK, this playbook) with new capabilities.

## 5. Observability expectations

- Tail log (`TailLogCell`) is the shared audit surface. Log any action that reshapes manifests, ops states, or automation scripts.
- Release log dashboard lives in the Relay UI (Release Log panel) and pulls from `/api/release-log`, which reads `data/logs/release.log`. Keep that file current (release pipeline + workflow harness already append entries) so Ops can trace every freeze cycle without touching the filesystem. The panel now renders `action`, `status`, `source`, duration chips, summary/error call-outs, and expandable step timelines, so populate those fields (and `timeline[].status/details`) whenever you emit entries from automation.
- Use `createTailLogEntry`/`appendTailLog` (frontend/backend) or `python scripts/relay_store.py tail-log-add` (CLI) to register those events so Ops never has to guess who triggered a workflow.
- Relay Health panel expects `scripts/capsule_status.py` output schema—maintain backward compatibility when modifying script fields.
- If auto-refresh features are added elsewhere, reuse the same localStorage pattern (`chatai.<feature>.autoRefresh`) for consistency.

## 6. Future hooks

- **Manifest regression suite:** Extend `scripts/manifest_validator.py` with a `--schema` switch once the Workshop defines a formal JSON schema so MCP can diff versions.
- **Ops relays in Storybook:** Mirror Relay Health panel stories so product reviews can toggle success/error states without hitting the backend.

## 7. Rapid rebrand automation blueprint

The rename that birthed the Horizon Relay Platform took dozens of manual steps. Re-run it (or apply future rebrands) with:

1. **Plan:** Update `configs/rebrand_plan.example.json` (or copy it) with the directory moves, notebook copies, text replacements, and validation commands you need.
2. **Dry run:** `python scripts/rebrand_reset.py --config your-plan.json --dry-run` lists every pending operation so you can sanity-check the scope.
3. **Apply:** Re-run without `--dry-run` to execute renames, copies, replacements, and validation commands in order. Abort automatically if a command fails unless `continue_on_error` is set for that entry.
4. **Iterate:** Because replacements are config-driven, you can add follow-up `find/replace` entries (e.g., `Kitchen → Workshop`, `playground → relay`) without rewriting ad-hoc scripts.
5. **Validate:** The `commands` array should include `python -m pytest`, `npm run check`, or any other health checks you care about. The script stops on the first failure so agents can fix issues immediately.

Use this workflow whenever a rename/reset looms—the scripted approach is faster, auditable, and repeatable compared to bespoke PowerShell sessions.

Document updates here whenever you add tools, scripts, or expectations so the next agent inherits the full picture.