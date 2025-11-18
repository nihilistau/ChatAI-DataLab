# Syntax Reference

Canonical naming + formatting rules for the ChatAI · DataLab stabilization phase.

## 1. Commit messages

```
<type>(<scope>): <imperative summary>

Body: Optional justification, include command output or artifact URLs.
Footer: Issues and checkpoints.
```

- **Allowed `type` values** during freeze: `fix`, `hardening`, `docs`, `ops`, `test`, `infra`.
- **Scopes** reference top-level areas (`backend`, `frontend`, `kitchen`, `scripts`, `docs`, `labctl`).
- **Summary** limited to 72 chars, must describe the bug or tightening action.
- **Footers**:
  - `Fixes #123`
  - `Checkpoint: 0012`
  - `Tag: v1.0.3-stability.20251116`

_Example_

```
fix(frontend): pin widget blueprint timeline rendering

- npm run test -- --runInBand
- npm run storybook:build

Fixes #742
Checkpoint: 0041
```

## 2. Branch names

```
stability/<issue-id>-<slug>
```

- Use lowercase kebab-case for the slug.
- Examples: `stability/742-blueprint-timeline`, `stability/755-diagnostics-timeout`.

## 3. Pull request titles

```
[type][scope] short summary (#issue-id)
```

- Example: `[fix][frontend] tighten widget showcase timeline (#742)`
- PR body must link to the issue, list local commands executed, and attach artifacts when applicable.

## 4. Tags

```
v<major>.<minor>.<patch>-stability.<YYYYMMDD>
```

- Example: `v1.0.3-stability.20251116`
- Annotate every tag with the associated checkpoint ID and milestone in the tag message.

## 5. Milestones

```
stability-week-<YYYYWW>
```

- Example: `stability-week-202547` (Week 47 of 2025).
- Close milestones only after: (a) all issues merged, (b) tag pushed, (c) checkpoint recorded.

## 6. Releases

```
Release: v<major>.<minor>.<patch>-stability.<YYYYMMDD>
```

- Release description must include:
  - Checklist link (`docs/RELEASE_CHECKLIST.md` section)
  - Integrity checkpoint ID
  - Links to CI run + artifacts
  - List of closed issues

## 7. Labels

Mandatory GitHub labels per PR / issue:

| Label | Purpose |
| --- | --- |
| `type:bug` | Defect discovered in production/testing |
| `type:hardening` | Refactor or resilience work |
| `priority:blocker|high|normal` | Drives milestone planning |
| `needs-checkpoint` | Remains until `scripts/project_integrity.py checkpoint` is recorded |
| `needs-tag` | Remains until annotated tag is pushed |

## 8. Job naming

Reference CI jobs exactly as defined under `.github/workflows/kitchen-notebooks.yml` when discussing failures:
`backend-tests`, `kitchen-tests`, `frontend-qa`, `storybook-builds`, `integrity-scan`.

## 9. Search Toolkit presets

- Use preset names like `bug-hunt`, `log-review`, `integrity-diff` when invoking `Search-LabRepo`.
- Log outputs to `logs/search-history.jsonl` with entries formatted as:
  `{ "preset": "bug-hunt", "timestamp": "2025-11-16T12:00:00Z", "paths": [...] }`

Keep this file updated whenever syntax conventions change. Failing to follow these formats blocks merges during the freeze. 