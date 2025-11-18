# v1.0.3-control-capsules.20251118 — Kitchen-first telemetry bundle

📘 **Operations Handbook:** https://github.com/nihilistau/ChatAI-DataLab/blob/v1.0.3-control-capsules.20251118/docs/OPERATIONS_HANDBOOK.md

## Highlights
- **Notebook relocation, validated.** All operational notebooks now live under `kitchen/notebooks/`. The release bundle ships the freshly executed Kitchen versions so downstream teams stop depending on the archived DataLab tree.
- **Telemetry ledger + Parquet extracts.** `python -m scripts.search_telemetry ingest ... --runs-parquet --daily-parquet` now feeds this bundle. Operators receive JSON + Arrow outputs for the search ledger, mirroring the Control Center dashboard and analytics workflows.
- **Ops-ready evidence.** Papermill snapshots (Search Telemetry, Ops Response Playbook, Widget Showcase) were rerun against the regenerated ledger to ensure the new paths and parameters hold up before tagging.

## Validation
- pip install -r kitchen/requirements.txt
- pip install -r datalab/requirements.txt
- python -m scripts.search_telemetry ingest --log-path logs/search-history.jsonl --output data/search_telemetry.json --runs-parquet data/search_telemetry-runs.parquet --daily-parquet data/search_telemetry-daily.parquet
- python -m papermill kitchen/notebooks/search_telemetry.ipynb kitchen/notebooks/_papermill/search_telemetry-release.ipynb -p SEARCH_LEDGER_PATH data/search_telemetry.json -p TELEMETRY_LOG_PATH logs/search-history.jsonl
- python -m papermill kitchen/notebooks/ops_response_playbook.ipynb kitchen/notebooks/_papermill/ops_response_playbook-release.ipynb -k python3
- python -m papermill kitchen/notebooks/widget_showcase.ipynb kitchen/notebooks/_papermill/widget_showcase-release.ipynb -k python3
- python -m pytest tests/test_search_ledger.py -q
- python -m scripts.project_integrity status

## Release artifacts to upload
Attach these assets from `release_artifacts/v1.0.3-control-capsules.20251118/`:

1. `control-center-dist.zip`
2. `storybook-static.zip`
3. `storybook-static-playground.zip`
4. Telemetry ledger exports:
   - `data/search_telemetry.json`
   - `data/search_telemetry-runs.parquet`
   - `data/search_telemetry-daily.parquet`
5. Notebook evidence (Kitchen snapshots):
   - `notebooks/search_telemetry-executed.ipynb`
   - `notebooks/ops_response_playbook.ipynb`
   - `notebooks/widget_showcase.ipynb`

## Operator callouts
- All manifest-driven notebooks now reference `kitchen.*` helpers. Mention the relocation in release notes so external collaborators stop editing `legacy/datalab/notebooks/*`.
- Highlight that the Parquet exports now accompany every release bundle, giving Ops lightweight access to per-run and per-day aggregates without standing up SQLite.
- When demonstrating the telemetry notebook, remind folks they can regenerate with `python -m scripts.search_telemetry ingest ...` plus Papermill to keep the evidence fresh.

## Next steps
- Update the remaining automation + tests (e.g., `tests/test_notebooks.py`) to execute Kitchen notebooks directly so CI stops depending on the archived DataLab copies.
- Continue migrating the lingering DataLab shims/tests so we can delete the legacy package after the next release cycle.
