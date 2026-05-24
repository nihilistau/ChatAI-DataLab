# Workshop + DataLab Merge Plan · Completed November 18, 2025

Workshop now fully supersedes the old DataLab namespace. This document serves as
the historical record of the migration and the checklist we used while deleting
the legacy package. All active helpers live under `workshop.*`, while
`legacy/datalab` contains read-only notebook copies for posterity.

> **Status**: All phases finished on 2025-11-18. The DataLab package no longer
> exists, release bundles point exclusively to Workshop assets, and only
> documentation references (e.g., this file) mention DataLab by name.

## Goals

1. **Single source of truth** – All helper modules (paths, diagnostics,
   widgets, telemetry scripts) should resolve through `workshop.*`.
2. **Zero downtime for notebooks** – Existing DataLab notebooks keep working
   until they are ported, thanks to compatibility shims.
3. **Progressive migration** – Contributors can move one module at a time,
   following a checklist and automated tests.
4. **Observability + docs** – The repo clearly states which pieces are legacy
   and where new work belongs.
5. **Provider-aware storage** – Workshop + DataLab assets rely on the shared
   Relay data store abstraction (SQLite, JSON, Cosmos) so CI, notebooks,
   and Ops tooling stay in sync regardless of which provider is enabled.

## Phased approach

| Phase | Description | Exit criteria |
| --- | --- | --- |
| 1. Shim (complete) | `workshop/__init__.py` re-exported the DataLab helper surface so new code could import `workshop`. Regression tests plus docs landed with the shim. | ✅ `from workshop import data_path` worked everywhere; `tests/test_workshop_bridge.py` kept the bridge covered until removal. |
| 2. Module migration | Move individual modules (paths, diagnostics, recipes, scripts) under `workshop/` and update the former DataLab namespace to re-export from the new location. Track progress in this file. | ✅ Every migrated module lived under `workshop/*` until the shim was deleted in Nov 2025. |
| 3. Sunset | Once all imports stop referencing the DataLab namespace, delete the legacy package (after a release branch) and remove compatibility shims. | ✅ Package removed 2025-11-18; only documentation mentions `legacy/datalab`. |

## Migration checklist per module

1. Move implementation from the former DataLab module (`<module>.py`) to `workshop/<module>.py`.
2. Update imports across the repo to point at `workshop.<module>`.
3. Replace the legacy file with a compatibility stub:
   ```python
   from workshop.<module> import *  # noqa: F401,F403
   ```
4. Add or update tests to exercise the Workshop path.
5. Document the change in:
   - `docs/WORKSHOP_MERGE_PLAN.md` (this file)
   - `docs/AGENT_OPERATIONS.md`
   - Release notes / changelog as needed.

> **Note:** Step 3’s shims were temporary. Once the DataLab package was deleted, the
> compatibility files disappeared and only historical notebook copies remained
> under `legacy/datalab`.

## Module migration tracker

| Module | Status | Notes |
| --- | --- | --- |
| `lab_paths` | ✅ Moved | Implementation now lives in `workshop/lab_paths.py`; the temporary DataLab shim was removed with the package. |
| `diagnostics` | ✅ Moved | Helpers now live in `workshop/diagnostics.py`; no shim remains because the DataLab package was deleted. |
| `widgets` | ✅ Moved | Widget dataclasses + catalog builders live in `workshop/widgets/`. Historical DataLab code exists only in `legacy/datalab`. |
| `elements.schema` | ✅ Moved | Catalog + helpers reside in `workshop/elements/schema.py`; references to the old namespace persist only in documentation. |
| `manifests` | ✅ Moved | Schema + validator live in `workshop/manifests/`; CLI + tests import Workshop directly, and the shim vanished alongside the DataLab namespace. |

### Post-migration follow-ups

1. **Consumer cleanup (docs + tooling sweeps)**
   - Keep auditing documentation, notebooks, and automation I/O for stray non-legacy references to the old DataLab namespace.
   - Use `git grep -n` against the literal old namespace to ensure hits live only in `legacy/` assets or historical write-ups like this file.

#### Consumer cleanup tracker

| Consumer | Status | Notes |
| --- | --- | --- |
| `scripts/control_health.py` | ✅ Updated | Imports now flow through `workshop.diagnostics` + `workshop.lab_paths`, so the health probe exercises the Workshop namespace directly. |
| Operational notebooks (former DataLab notebooks) | ✅ Relocated | Notebooks were copied into `workshop/notebooks/` and the entire legacy tree now lives under `legacy/datalab/notebooks/`. The original directory contains a README pointing contributors to the Workshop path. |
| Release bundles (`release_artifacts/*`) | ✅ Updated | `v1.0.3-control-relays.20251118` ships Workshop notebooks plus JSON + Parquet telemetry outputs, so release bundles no longer reference the retired DataLab paths. |
| Release automation (`scripts/release_checklist.ps1`, docs) | ✅ Updated | LabControl + release docs default to Workshop notebooks and surface `workshop/notebooks/_papermill` artifact guidance. |
| Shim regression tests (former DataLab suite) | ✅ Removed | Redundant suites deleted after migrating coverage into `workshop/tests/*` on 2025-11-18. |

Ongoing maintenance: continue scrubbing docs, workflows, and telemetry surfaces so non-historical references point to Workshop only.
2. **Legacy retirement (DONE)**
   - Package deletion + release comms landed with the 2025-11-18 cleanup.

   **Retirement gating checklist (validated 2025-11-18)**
   - [x] `grep -R "from datalab"` returns only doc/release references.
   - [x] `datalab/notebooks/` tree archived under `legacy/` (read-only) so new edits target `workshop/notebooks/`.
   - [x] Shim regression tests moved/rewritten under `workshop/tests/` or removed entirely.
   - [x] Release notes + `docs/CHANGELOG.md` call out the removal to downstream notebook owners.
   - [x] After the release was tagged, the `datalab/` package was deleted and automation imports were updated.

### Datastore + telemetry alignment

- The active Relay data store (configured in `configs/lab_environment_config.md`) must be accessed through `relay/backend/app/services/data_store.py` or its CLI wrappers (`scripts/relay_store.py summary|interactions|tail-log`). Stop opening SQLite files directly; Ops should rely on these helpers so JSON/Cosmos providers keep working.
- Workshop notebooks and automations should default `DB_PATH="auto"` and call helpers such as `workshop.scripts.metrics.load_interactions()` to hydrate DataFrames. This keeps Papermill, CI, and `scripts/control_center.py notebook --db-path auto` on the same execution path.
- Telemetry entry points (e.g., `workshop/telemetry/search_ledger.py`, frontend widgets, manifest consumers) must emit tail log events via `createTailLogEntry`, `appendTailLog`, or `scripts/relay_store.py tail-log-add`. This gives Ops parity across providers and exposes ingestion steps in the Control Center tail log.

### Search telemetry ledger migration

- **Chosen approach**: land a JSON/Parquet ledger first, then wire Cosmos (or any remote store) behind the same interface. This keeps ingestion fast, portable, and test-friendly while leaving room for managed storage once Ops is ready.
- **Why not Cosmos-only?**
   - Agents and CI can hydrate local telemetry without credentials.
   - JSON artifacts drop cleanly into MCP decking, release bundles, and Git history for auditability.
   - When Cosmos is introduced, we can stream the same normalized events into it without rewriting the ingestion flow.
- **Implementation checklist**
   1. Create `workshop/telemetry/search_ledger.py` to normalize log lines, compute aggregates, and write `data/search_telemetry.json` + optional Parquet extracts.
      - ✅ JSON output ships today; pass `--runs-parquet` / `--daily-parquet` to emit Arrow-native tables for downstream analytics.
   2. Retire the legacy search telemetry script that previously lived under the DataLab namespace after verifying the Workshop helper parity.
      - ✅ Completed: the Workshop CLI is the sole entrypoint; the legacy script disappeared with the package removal.
   3. Update `chatai/backend/app/services/search_telemetry.py` (plus tests) to read the JSON snapshot; keep a fast-path to recompute on the fly if the artifact is missing.
   4. Document the new command + artifact in `README.md`, `docs/OPS_COMMANDS.md`, and subsystem health docs so Ops knows the SQLite requirement is gone.
   5. After a release cycle without regressions, delete any remaining `data/search_telemetry.db` artifacts and rip out the SQLite-backed helpers so the JSON ledger is the only supported path.
   6. Keep tail-log events flowing: ingestion + migrations already emit Control Center tail log entries via `TailLogEntryCreate`. Leave that hook on (or add a CLI flag if tests need silence) so Ops can trace every ledger change.

## Command + script mapping (historical reference)

| Legacy / historical path | Current Workshop path | Notes |
| --- | --- | --- |
| Former DataLab search telemetry script (removed) | `workshop/scripts/search_telemetry.py` | Workshop CLI is canonical; the legacy script was deleted with the package. |
| `legacy/datalab/notebooks/*` | `workshop/notebooks/*` | `legacy/datalab` holds read-only snapshots for archaeology; all edits target Workshop. |
| `from DataLab import data_path` (historical) | `from workshop import data_path` | Import the Workshop helper directly; shim tests were deleted after the sunset. |
| Manual SQLite shell / dumps | `python scripts/relay_store.py summary`, `python scripts/relay_store.py interactions --limit 20`, `python scripts/relay_store.py tail-log` | Provider-aware CLI keeps SQLite/JSON/Cosmos paths aligned, including Cosmos/JSON stores. |

## Ongoing maintenance

- Continue repo-wide greps for the retired namespace string to ensure references live only in
   `legacy/` or historical documentation.
- Keep `legacy/datalab` read-only; new notebooks and telemetry scripts belong in
   `workshop/`.
- When introducing fresh automation entry points, update this file plus Ops docs
   so future readers understand the Workshop-only world.
