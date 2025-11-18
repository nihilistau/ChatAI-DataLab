# Playground · DataLab — Copilot & Agent Guardrails

These prompts keep every agent aligned with the manifest-driven workflow, Ops tooling, and validation standards. Reference them when coding, running automations, or wiring new MCP helpers.

## Golden rules

1. **Manifest context is canonical.** Always import from `src/context/ManifestContext` and consume manifest data via `useManifest()`. Never fetch `/api/playgrounds/*/manifests` directly from components—let the provider handle retries, auto-refresh, and logging.
2. **Keep telemetry flowing.** Whenever you add a new manifest consumer (components, hooks, Storybook), emit meaningful events to the tail log via `createTailLogEntry` or reuse `appendTailLog` patterns so Ops traces remain explorable.
3. **Validate before you brag.** Run `npm run check` inside `playground/frontend` after frontend edits, `pytest` for backend updates, and `python scripts/project_integrity.py` before shipping infra changes. Surface failures—including linter output—in your summary.
4. **Respect Kitchen → Control contracts.** Layouts come from the Kitchen notebooks; control-surface components must treat manifest metadata as user input. Guard against missing sections, empty widget arrays, and undefined actions.
5. **Prefer scripts over guesswork.** Use `python scripts/control_center.py` for orchestrator flows, `scripts/capsule_status.py` for capsule telemetry, and the Vite scripts in `playground/frontend/package.json` for UI work (`dev`, `build`, `storybook`, `check`).

## Manifest-specific guidance

- The provider exposes `{ manifest, refresh, refreshing, autoRefreshEnabled, setAutoRefreshEnabled, lastFetched }`. Wire refresh buttons + toggles through those props instead of re-implementing state.
- Every manifest sync should log `manifest · {playground} rev X synced` to the tail log. If you duplicate that behavior, dedupe via a ref keyed by checksum to avoid log spam.
- When building new tiles/cards, lean on shared styles: `.manifest-panel`, `.manifest-summary-card`, `.intel-card`. This keeps the UI consistent with Ops telemetry.
- Storybook stories should wrap components in `ManifestProvider` with knobs for tenant/playground so designers can preview multiple outputs.

## MCP / tooling expectations

- Treat MCP servers as first-class citizens. If a workflow can be automated (linting, manifest publishing, notebook runs), prefer creating a capsule/script under `scripts/` or `kitchen/` and expose it through MCP so other agents can reuse it.
- Capture new automation entry points inside `docs/AGENT_OPERATIONS.md` (see below) and link any bespoke commands.
- When you introduce a new MCP command, document required environment variables, secrets, and how outputs feed back into the Control Center.

## Documentation + reporting

- Update `README.md` whenever you add a new surface or capability to the control center—especially panels fed by manifests.
- Add test coverage or Storybook stories for new manifest-driven components when practical.
- Summaries must mention:
	1. Files touched and the intent.
	2. Commands/tests executed and their status.
	3. Any follow-up items or TODOs, even if deferred.

Stay within these guardrails and the agents stay fast, predictable, and observable. Deviate only with a compelling reason documented in the PR.*** End Patch
