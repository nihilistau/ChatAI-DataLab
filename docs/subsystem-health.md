# Subsystem health audit — 2025-11-17

| Subsystem | Current signal | Confidence | Action items |
| --- | --- | --- | --- |
| Backend API + tests | `python -m pytest` (55 tests) ✅, control scripts operational after `sys.path` fix. | High | Monitor `uvicorn` install paths in orchestrator logs; consider bundling backend venv bootstrap into LabControl start.
| Frontend build + tooling | `npm run check`, `npm run build`, `npm run test`, `npm run storybook:build` ✅ after Vite 7 + happy-dom 20 bump. | High | Add Storybook smoke to release checklist; schedule Vite/esbuild optional dependency cleanup for Linux hosts still hitting rollup native warnings.
| Control Center scripts | `python scripts/control_center.py status` ✅ (snapshot saved under `.labctl/state/aggregate.json`, logs still show missing `uvicorn`/`jupyter` on prior hosts). | Medium | Provide friendlier error when orchestrator sees missing uvicorn/Jupyter; maybe stash recommended install commands in output/README troubleshooting.
| Kitchen / DataLab parity | Papermill CLI ✅ — `control_center_playground-cli-20251117-052129.ipynb` + `control_center_snapshot.json` emitted under `datalab/notebooks/_papermill/`. Kitchen shims still backed by pytest. | Medium-High | Reference the snapshot JSON when triaging Ops signals; ensure `kitchen/requirements.txt` stays in sync with datalab shim and schedule next run after manifest changes.
| Documentation | README + Agent Playbook updated through Kitchen migrations; new audit log recorded here. | High | Link this file from `docs/OPERATIONS_HANDBOOK.md` under health checks section.
| Integrity tooling | `python scripts/project_integrity.py status` reports 120 added / 32 deleted / 65 modified files (mostly artifacts + Kitchen migration files). | Medium | Curate ignore list or checkpoint once new baseline is intentional; ensure dist/storybook outputs aren’t committed before tagging.

## Control Center telemetry snapshot

- Latest run: `datalab/notebooks/_papermill/control_center_playground-cli-20251117-052129.ipynb`
- Tail log + service summary: `datalab/notebooks/_papermill/control_center_snapshot.json`
- When updating this table, skim the JSON for `service_states`, `prompt_count`, and `fallback_reason` so Ops always sees fresh Control Center metrics alongside the narrative health notes.
