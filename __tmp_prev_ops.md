# Agent Operations Playbook

This playbook captures the high-trust patterns, scripts, and MCP entry points that keep ChatAI · DataLab agents effective across frontend, backend, and Kitchen workflows.

## 1. Quick-start scripts

| Task | Command | Notes |
| --- | --- | --- |
| Launch Control Center playground | `npm run playground:dev` (from `chatai/frontend`) | Uses `ManifestProvider` to hydrate UI panels. Ensure `.env` contains `VITE_PLAYGROUND_TENANT` and `VITE_PLAYGROUND_NAME`. |
| Run Ops orchestrator helpers | `python scripts/control_center.py <command>` | Supports `start`, `stop`, `status`, `notebook`, `elements`. Emits telemetry to `data/logs`. |
| Publish Kitchen manifest | `python kitchen/scripts/publish_manifest.py --tenant demo-tenant --playground welcome-control` | Wraps the `ManifestPublisher` helper introduced in the Welcome Cookbook. |
| Validate manifest locally | `python scripts/manifest_validator.py path/to/manifest.json --json` | Runs the Pydantic-based validator and emits MCP-friendly JSON summaries (supports `-` for stdin). |
| Capsule diagnostics | `python scripts/capsule_status.py --capsule control` | Mirrors the Capsule Health panel output. |
| Notebook snapshot (Papermill) | `python scripts/control_center.py notebook --db-path auto --status-url http://localhost:8000/api/control/status` | Executes `control_center_playground.ipynb` via Papermill with provider-aware datastore wiring; outputs land in `datalab/notebooks/_papermill`. Always keep `--db-path auto` unless you need to target a historical SQLite file. |
| Inspect datastore provider | `python scripts/playground_store.py summary` | Reveals the active provider (SQLite/JSON/Cosmos) and sample counts for interactions/artifacts/tail log. Pair with `interactions`, `artifacts`, `tail-log`, and `tail-log-add` subcommands for deeper inspection. |

> **Path helpers have moved.** Import `data_path`, `lab_path`, `logs_path`, and `get_lab_root` from `kitchen.lab_paths`. The legacy `datalab.lab_paths` module now re-exports those helpers so notebooks can migrate gradually.

> **Diagnostics + widgets are Kitchen-first.** Use `kitchen.diagnostics` for logging helpers (`append_diagnostic_record`, `record_run_metadata`, etc.) and `kitchen.widgets` for `WidgetSpec`, `WidgetLibrary`, and catalog builders. The `datalab` package simply forwards to these modules.

> **Manifest schema + validator live under Kitchen.** Import `PlaygroundManifest*` models and `validate_manifest_payload` from `kitchen.manifests` (or `kitchen.manifests.validator`). Legacy `datalab.manifests` just re-exports these helpers for notebooks that have not migrated yet.

> **Datastore CLI is the single source of truth.** `scripts/playground_store.py` talks to the exact store the backend uses, regardless of provider. Prefer these subcommands over ad-hoc `sqlite3` sessions and log every manual mutation via `tail-log-add` so Ops can trace the change.

## 2. Manifest-aware UI development

1. Wrap any manifest-consuming UI in `<ManifestProvider>` (already wired in `src/main.tsx`).
2. Use the `useManifest()` hook for data, refresh, auto-refresh toggle, and timestamps.
3. When adding a new panel:
   - Show loading, empty, and error states.
   - Log revisions (`manifest · {playground} rev {revision} synced`).
   - Keep data display defensive (guard against missing metadata, sections, widgets, actions).
4. Record the change in `README.md` and Storybook if it affects design reviewers.

## 3. MCP + automation hooks

- **Notebook runners:** All Kitchen notebooks surfaced via `scripts/control_center.py notebook <name>` automatically log to `data/logs/lab-diagnostics.jsonl`. Extend this script when adding new automation capsules so other agents inherit the telemetry.
- **Manifest ops:** Prefer using the `ManifestPublisher` helper. When scripting, import from `kitchen/helpers/manifest.py` (or the latest module) to reuse checksum + revision logic.
- **Manifest validator MCP command:** The Control Center now seeds `data/commands.json` with a `Manifest validator (onboarding)` entry tagged `manifest/mcp/validator`. Run it from the Ops Deck command list or via `GET /api/commands?tag=manifest` + `POST /api/commands/{id}/run` to emit the JSON summary from `scripts/manifest_validator.py` without reaching for a shell.
- **Datastore + tail logs:** CLI workflows that ingest telemetry or mutate artifacts should rely on `python scripts/playground_store.py ...` instead of direct DB access. Announce significant actions (ingest, migration, Papermill runs, manifest publish) with `python scripts/playground_store.py tail-log-add "<event>" --source <actor>` so the Control Center tail log mirrors automation.
- **Custom MCP tools:** When you register a new tool, capture its command, inputs, and outputs in this file. Include a short example invocation for future agents.

## 4. Validation checklist

Before landing changes:

1. **Frontend:**
   ```bash
   npm run check
   npm run build # optional but recommended before releases
   ```
2. **Backend / Kitchen:**
   ```bash
   pytest
   python scripts/project_integrity.py
   ```
3. **Docs:** Update relevant markdown (README, OPERATIONS_HANDBOOK, this playbook) with new capabilities.

## 5. Observability expectations

- Tail log (`TailLogCell`) is the shared audit surface. Log any action that reshapes manifests, ops states, or automation scripts.
- Use `createTailLogEntry`/`appendTailLog` (frontend/backend) or `python scripts/playground_store.py tail-log-add` (CLI) to register those events so Ops never has to guess who triggered a workflow.
- Capsule Health panel expects `scripts/capsule_status.py` output schema—maintain backward compatibility when modifying script fields.
- If auto-refresh features are added elsewhere, reuse the same localStorage pattern (`chatai.<feature>.autoRefresh`) for consistency.

## 6. Future hooks

- **Manifest regression suite:** Extend `scripts/manifest_validator.py` with a `--schema` switch once the Kitchen defines a formal JSON schema so MCP can diff versions.
- **Ops capsules in Storybook:** Mirror capsule status stories so product reviews can toggle success/error states without hitting the backend.

Document updates here whenever you add tools, scripts, or expectations so the next agent inherits the full picture.```}]]} Slew? need closing newline. content includes code fences. ensure ended newline. ok. tool output says file created maybe success? Need check. Let's confirm. Wait there is stray triple `? oh check content includes code fences. We'll verify file. Use read_file to confirm. թիմ. let's read. आती. We'll call read. Actually safe though. Use read_file. Need to note multiple code fences with same language? already in content. Good though. let's confirm. call read_file. Let's do. Need use tool? yes. provide impetus: verifying new doc. call read_file. but instructions says after read operations in parallel etc. Already created content maybe need verifying? I'll call read_file. but before tool call need preface 