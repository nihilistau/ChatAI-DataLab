# Tagging Standard

Tags align code comments, Ops Deck telemetry, DataLab notebooks, and the integrity manifest. Every source file must declare at least one tag via `# @tag:` (Python) or block comments (TS/TSX). This document lists the canonical values.

## 1. Tag catalog

| Tag | Description | Default owners |
| --- | --- | --- |
| `backend` | FastAPI services, database models, schemas | Backend maintainers |
| `api` | REST endpoints, routers | Backend maintainers |
| `models` | SQLAlchemy models, Pydantic schemas | Backend maintainers |
| `llm` | LLM clients, adapters | Backend maintainers |
| `ops` | Orchestrator, Ops Deck, lab control scripts | Platform/Ops |
| `ui` | Frontend components, styles, UX | Frontend maintainers |
| `canvas` | Canvas board logic, artifacts, hypotheses | Frontend maintainers |
| `tail-log` | Tail log integrations (UI + backend) | Full stack |
| `notebook` | DataLab notebooks, widgets | Data scientists |
| `metrics` | `datalab/scripts`, telemetry helpers | Data scientists |
| `telemetry` | Search/Ops telemetry ingestion, dashboards, notebooks | Data scientists + Platform |
| `integrity` | Hash/checkpoint tooling | Platform maintainers |
| `config` | Config manifests, policy files | Platform maintainers |
| `docs` | Markdown docs, tutorials, installation | Docs guild |
| `setup` | Installer scripts, environment bootstrap | Platform maintainers |
| `theme` | UI themes, CSS tokens | Frontend maintainers |
| `ops-log` | Ops log ingestion, TailLog bridging | Platform/Ops |

Additions require updating both this file and `configs/tags.json`.

## 2. Annotation syntax

### Python

```python
"""Ops Tail log API."""
# @tag:backend,ops,tail-log
```

### TypeScript / React

```tsx
/* @tag:ui,canvas */
```

### Notebooks

- Insert a markdown cell at the top: `**Tags:** notebook,metrics`

## 3. Tagging rules

1. Prefer 1–3 tags per file; max 5.
2. Keep tags lowercase, hyphen-separated.
3. If you introduce a new subsystem, add the tag to this file + `configs/tags.json` and describe ownership.
4. The integrity CLI parses tags automatically; do not change the `@tag:` prefix.

## 4. Usage examples

- `chatai/backend/app/api/routes.py` → `# @tag:backend,api,ops`
- `chatai/frontend/src/components/TailLogCell.tsx` → `/* @tag:ui,tail-log */`
- `scripts/project_integrity.py` → `# @tag:setup,integrity`

Tags drive filtered integrity reports (`--tags ops`) and future automation (e.g., Ops Deck filtering). Make them meaningful and consistent.
