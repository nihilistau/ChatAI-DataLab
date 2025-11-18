# Kitchen + DataLab Merge Plan · Completed November 18, 2025

Kitchen now fully supersedes the old DataLab namespace. This document serves as
the historical record of the migration and the checklist we used while deleting
the legacy package. All active helpers live under `kitchen.*`, while
`legacy/datalab` contains read-only notebook copies for posterity.

> **Status**: All phases finished on 2025-11-18. `datalab/` no longer exists,
> release bundles point exclusively to Kitchen assets, and only documentation
> references (e.g., this file) mention DataLab by name.

## Goals

1. **Single source of truth** – All helper modules (paths, diagnostics,
   widgets, telemetry scripts) should resolve through `kitchen.*`.
2. **Zero downtime for notebooks** – Existing DataLab notebooks keep working
   until they are ported, thanks to compatibility shims.
3. **Progressive migration** – Contributors can move one module at a time,
   following a checklist and automated tests.
4. **Observability + docs** – The repo clearly states which pieces are legacy
   and where new work belongs.
5. **Provider-aware storage** – Kitchen + DataLab assets rely on the shared
   Playground data store abstraction (SQLite, JSON, Cosmos) so CI, notebooks,
   and Ops tooling stay in sync regardless of which provider is enabled.

## Phased approach

| Phase | Description | Exit criteria |
| --- | --- | --- |
| 1. Shim (complete) | `kitchen/__init__.py` re-exported the DataLab helper surface so new code could import `kitchen`. Regression tests plus docs landed with the shim. | ✅ `from kitchen import data_path` worked everywhere; `tests/test_kitchen_bridge.py` kept the bridge covered until removal. |
| 2. Module migration | Move individual modules (paths, diagnostics, recipes, scripts) under `kitchen/` and update `datalab/` to re-export from the new location. Track progress in this file. | ✅ Every migrated module lived under `kitchen/*` until the shim was deleted in Nov 2025. |
| 3. Sunset | Once all imports stop referencing `datalab`, delete the legacy package (after a release branch) and remove compatibility shims. | ✅ `datalab/` removed 2025-11-18; only documentation mentions `legacy/datalab`. |

## Migration checklist per module

1. Move implementation from `datalab/<module>.py` to `kitchen/<module>.py`.
2. Update imports across the repo to point at `kitchen.<module>`.
3. Replace the legacy file with a compatibility stub:
   ```python
   from kitchen.<module> import *  # noqa: F401,F403
   ```
4. Add or update tests to exercise the Kitchen path.
5. Document the change in:
   - `docs/KITCHEN_MERGE_PLAN.md` (this file)
   - `docs/AGENT_OPERATIONS.md`
   - Release notes / changelog as needed.

> **Note:** Step 3’s shims were temporary. Once `datalab/` was deleted, the
> compatibility files disappeared and only historical notebook copies remained
> under `legacy/datalab`.

## Module migration tracker

| Module | Status | Notes |
| --- | --- | --- |
| `lab_paths` | ✅ Moved | Implementation now lives in `kitchen/lab_paths.py`; the temporary `datalab/lab_paths.py` shim was removed with the package. |
| `diagnostics` | ✅ Moved | Helpers now live in `kitchen/diagnostics.py`; no shim remains because `datalab/` was deleted. |
| `widgets` | ✅ Moved | Widget dataclasses + catalog builders live in `kitchen/widgets/`. Historical DataLab code exists only in `legacy/datalab`. |
| `elements.schema` | ✅ Moved | Catalog + helpers reside in `kitchen/elements/schema.py`; references to the old namespace persist only in documentation. |
| `manifests` | ✅ Moved | Schema + validator live in `kitchen/manifests/`; CLI + tests import Kitchen directly, and the shim vanished alongside `datalab/`. |

### Post-migration follow-ups

1. **Consumer cleanup (docs + tooling sweeps)**
   - Keep auditing documentation, notebooks, and automation I/O for stray non-legacy `datalab` references.
   - Use `git grep -n "datalab"` to ensure hits live only in `legacy/` assets or historical write-ups like this file.

#### Consumer cleanup tracker

| Consumer | Status | Notes |
| --- | --- | --- |
| `scripts/control_health.py` | ✅ Updated | Imports now flow through `kitchen.diagnostics` + `kitchen.lab_paths`, so the health probe exercises the Kitchen namespace directly. |
| Operational notebooks (`datalab/notebooks/*`) | ✅ Relocated | Notebooks were copied into `kitchen/notebooks/` and the entire legacy tree now lives under `legacy/datalab/notebooks/`. The original `datalab/notebooks` directory contains a README pointing contributors to the Kitchen path. |
| Release bundles (`release_artifacts/*`) | ✅ Updated | `v1.0.3-control-capsules.20251118` ships Kitchen notebooks plus JSON + Parquet telemetry outputs, so release bundles no longer reference `datalab/notebooks`. |
| Release automation (`scripts/release_checklist.ps1`, docs) | ✅ Updated | LabControl + release docs default to Kitchen notebooks and surface `kitchen/notebooks/_papermill` artifact guidance. |
| Shim regression tests (`datalab/tests/*`) | ✅ Removed | Redundant suites deleted after migrating coverage into `kitchen/tests/*` on 2025-11-18. |

Ongoing maintenance: continue scrubbing docs, workflows, and telemetry surfaces so non-historical references point to Kitchen only.
2. **Legacy retirement (DONE)**
   - Package deletion + release comms landed with the 2025-11-18 cleanup.

   **Retirement gating checklist (validated 2025-11-18)**
   - [x] `grep -R "from datalab"` returns only doc/release references.
   - [x] `datalab/notebooks/` tree archived under `legacy/` (read-only) so new edits target `kitchen/notebooks/`.
   - [x] Shim regression tests moved/rewritten under `kitchen/tests/` or removed entirely.
   - [x] Release notes + `docs/CHANGELOG.md` call out the removal to downstream notebook owners.
   - [x] After the release was tagged, the `datalab/` package was deleted and automation imports were updated.

### Datastore + telemetry alignment

- The active Playground data store (configured in `configs/lab_environment_config.md`) must be accessed through `playground/backend/app/services/data_store.py` or its CLI wrappers (`scripts/playground_store.py summary|interactions|tail-log`). Stop opening SQLite files directly; Ops should rely on these helpers so JSON/Cosmos providers keep working.
- Kitchen notebooks and automations should default `DB_PATH="auto"` and call helpers such as `kitchen.scripts.metrics.load_interactions()` to hydrate DataFrames. This keeps Papermill, CI, and `scripts/control_center.py notebook --db-path auto` on the same execution path.
- Telemetry entry points (e.g., `kitchen/telemetry/search_ledger.py`, frontend widgets, manifest consumers) must emit tail log events via `createTailLogEntry`, `appendTailLog`, or `scripts/playground_store.py tail-log-add`. This gives Ops parity across providers and exposes ingestion steps in the Control Center tail log.

### Search telemetry ledger migration

- **Chosen approach**: land a JSON/Parquet ledger first, then wire Cosmos (or any remote store) behind the same interface. This keeps ingestion fast, portable, and test-friendly while leaving room for managed storage once Ops is ready.
- **Why not Cosmos-only?**
   - Agents and CI can hydrate local telemetry without credentials.
   - JSON artifacts drop cleanly into MCP decking, release bundles, and Git history for auditability.
   - When Cosmos is introduced, we can stream the same normalized events into it without rewriting the ingestion flow.
- **Implementation checklist**
   1. Create `kitchen/telemetry/search_ledger.py` to normalize log lines, compute aggregates, and write `data/search_telemetry.json` + optional Parquet extracts.
      - ✅ JSON output ships today; pass `--runs-parquet` / `--daily-parquet` to emit Arrow-native tables for downstream analytics.
   2. Retire `datalab/scripts/search_telemetry.py` after verifying the Kitchen helper parity.
      - ✅ Completed: the Kitchen CLI is the sole entrypoint; the legacy script disappeared with the package removal.
   3. Update `chatai/backend/app/services/search_telemetry.py` (plus tests) to read the JSON snapshot; keep a fast-path to recompute on the fly if the artifact is missing.
   4. Document the new command + artifact in `README.md`, `docs/OPS_COMMANDS.md`, and subsystem health docs so Ops knows the SQLite requirement is gone.
   5. After a release cycle without regressions, delete any remaining `data/search_telemetry.db` artifacts and rip out the SQLite-backed helpers so the JSON ledger is the only supported path.
   6. Keep tail-log events flowing: ingestion + migrations already emit Control Center tail log entries via `TailLogEntryCreate`. Leave that hook on (or add a CLI flag if tests need silence) so Ops can trace every ledger change.

## Command + script mapping (historical reference)

| Legacy / historical path | Current Kitchen path | Notes |
| --- | --- | --- |
| `datalab/scripts/search_telemetry.py` (removed) | `kitchen/scripts/search_telemetry.py` | Kitchen CLI is canonical; the legacy script was deleted with the package. |
| `legacy/datalab/notebooks/*` | `kitchen/notebooks/*` | `legacy/datalab` holds read-only snapshots for archaeology; all edits target Kitchen. |
| `from datalab import data_path` (removed) | `from kitchen import data_path` | Import the Kitchen helper directly; shim tests were deleted after the sunset. |
| Manual SQLite shell / dumps | `python scripts/playground_store.py summary`, `python scripts/playground_store.py interactions --limit 20`, `python scripts/playground_store.py tail-log` | Provider-aware CLI keeps SQLite/JSON/Cosmos paths aligned, including Cosmos/JSON stores. |

## Ongoing maintenance

- Continue repo-wide greps for `datalab` to ensure references live only in
   `legacy/` or historical documentation.
- Keep `legacy/datalab` read-only; new notebooks and telemetry scripts belong in
   `kitchen/`.
- When introducing fresh automation entry points, update this file plus Ops docs
   so future readers understand the Kitchen-only world.
