# File System Blueprint & Guardrails

This repo enforces a predictable layout so automation, Ops Deck, notebooks, and contributors speak the same language. Treat this document as the single source of truth whenever you add files, rename directories, or create tags.

## 1. Top-level tree

```
ChatAI-DataLab/
├── playground/             # Frontend + backend apps
├── controlplane/            # Cross-platform orchestrator
├── kitchen/                 # Active notebooks, scripts, metrics helpers
├── legacy/
│   └── datalab/             # Read-only historical notebooks/scripts
├── data/                    # Databases, exported datasets
├── docs/                    # This guide, tutorials, install notes
├── configs/                 # Hash/tagging manifests & templates
├── scripts/                 # Setup + orchestration (bash + pwsh)
├── .project_integrity/      # Hash manifests + checkpoints (generated)
├── backups/                 # Human-friendly release/repair bundles
└── PROJECT_OVERVIEW.md      # Narrative plan
```

> `.project_integrity/` and `backups/` are created when you run `project_integrity.py`. They remain in `.gitignore` unless you intentionally commit snapshots.

## 2. Ownership zones

| Zone | Owner | Contains | Guardrails |
| --- | --- | --- | --- |
| `playground/frontend` | UI | React components, styles, lib APIs | Only TypeScript/TSX; tag files with `@tag:ui` + feature-specific tags |
| `playground/backend` | API | FastAPI app, SQLAlchemy models, services | Python only; keep modules under 400 LOC and use section banners |
| `controlplane` | Ops | Orchestrators for Ops Deck, CLI, PowerShell | Avoid hard-coded paths; tag `@tag:ops` |
| `kitchen` | Insights | Notebooks, scripts, metrics helpers | Keep notebooks in `notebooks/`; helper modules under `scripts/` |
| `legacy/datalab` | Historical reference | Archived copies of notebooks/scripts from the pre-Kitchen era | Read-only; reference only when porting older work |
| `configs` | Governance | `tags.json`, `integrity.json`, policy files | JSON/TOML only; referenced by tooling |
| `scripts` | Tooling | Setup, lab control, integrity CLI | Sectioned comments; mention supported shells |

## 3. Naming conventions

- **Directories**: lowercase with hyphens (`hypothesis-decks`), except language-specific defaults (`__pycache__`).
- **Python modules**: snake_case; include module docstring with `@tag` annotations.
- **TypeScript/React**: PascalCase components, camelCase hooks/utilities.
- **Notebooks**: snake_case with domain prefix (`hypothesis_control.ipynb`).
- **Config files**: `.json` or `.toml`; prefer descriptive prefixes (`hash_manifest.json`).

## 4. Comment sections

Every Python/TS file should include top-level banners:

```python
# --- Imports ---------------------------------------------------------------
from fastapi import FastAPI

# --- Constants -------------------------------------------------------------
OPS_POLL_INTERVAL_MS = 25000

# --- FastAPI application ---------------------------------------------------
```

Add `# @tag:` annotations near the top so the integrity CLI can index ownership:

```python
# @tag:backend,api
# @tag:llm
```

For React components, mirror this inside block comments:

```tsx
/* --------------------------------------------------------------------------
 * Component: OpsDeck
 * @tag:ui,ops
 * ------------------------------------------------------------------------ */
```

## 5. Config + backup locations

| Path | Purpose |
| --- | --- |
| `configs/tags.json` | Canonical list of tags, owners, descriptions |
| `configs/integrity_policy.json` | Hashing + repair options (exclusions, backup depth) |
| `.project_integrity/index.json` | Generated manifest of every tracked file |
| `.project_integrity/backups/<timestamp>/` | Auto-created directories containing archived files |
| `backups/<label>.zip` | Human-readable archives created via LabControl or `project_integrity.py export` |

## 6. Milestones & tags

- Each checkpoint gets `tag`, `milestone`, `reason`, and `timestamp` fields.
- Tags must exist in `configs/tags.json`; if you need a new tag update that file + `docs/TAGS.md`.
- Guardrail: never delete manifest history—create new checkpoints instead.

## 7. Adding new modules

1. Determine the ownership zone (table above).
2. Update `docs/FILE_SYSTEM.md` if you add a new directory at the top level.
3. Add tags to `configs/tags.json` if necessary.
4. Run `python scripts/project_integrity.py checkpoint --reason "Added <feature>"` once the file lands.

This structure is designed for automation. If a file strays from these rules the integrity CLI will flag it so you can correct the path or update this document.
