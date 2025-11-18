# v1.0.2-control-capsules.20251116 — Control Capsule Bootstrap

📘 **Operations Handbook:** https://github.com/nihilistau/ChatAI-DataLab/blob/v1.0.2-control-capsules.20251116/docs/OPERATIONS_HANDBOOK.md (canonical capsule guide)

## Highlights
- **Backend guardrails** (ix(backend): harden guardrails and command services)
  - Tightened FastAPI validation, safer command routing, and better diagnostics for Ops Deck telemetry ingestion.
- **Frontend ops design system** (hardening(frontend): expand ops design system)
  - Refreshed blueprint tokens, Control Center widgets, Storybook playground coverage, and rebuilt dist/storybook assets.
- **Doc + workflow codification** (docs(ops): codify stability guardrails, chore(release): publish control capsule handbook)
  - New Operations Handbook, release checklist updates, and handbook-driven integrity workflow for future capsules.
- **DataLab + scripts bundle** (eat(datalab): wire control center lab assets)
  - Search telemetry ingestion CLI, widget samples, notebook refreshes, and PowerShell helpers for lab bootstrap + release automation.

## Validation
- python -m pytest datalab/tests -q
- python -m pytest tests/test_notebooks.py -q
- python scripts/project_integrity.py status --baseline v1.0.1-stability.20251116
- python scripts/project_integrity.py status

## Release artifacts to upload
Attach these assets directly from `release_artifacts/v1.0.2-control-capsules.20251116/`:

1. `control-center-dist.zip`
2. `storybook-static.zip`
3. `storybook-static-playground.zip`
4. Notebooks (upload individually):
  - `notebooks/search_telemetry-executed.ipynb`
  - `notebooks/ops_response_playbook.ipynb`
  - `notebooks/widget_showcase.ipynb`

## Operator callouts
- Point readers to docs/OPERATIONS_HANDBOOK.md for the Control Capsule workflow and to the refreshed docs/RELEASE_CHECKLIST.md for artifact guidance.
- Highlight the three grouped commits (backend hardening, frontend design system, DataLab bundle) along with the new handbook commit.
- Mention the new project_integrity.py status --baseline <tag> switch so others can diff against any previous checkpoint/tag.

## Next steps
- Start the bootstrap capsule initiative (capsule manifests, default onboarding environment) per docs/GOALS_AND_ACHIEVEMENTS.md.
- Track future work around capsule save/load + managed DB migration.
