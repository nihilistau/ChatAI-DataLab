# Integrity, Hashing & Repair Guide

`scripts/project_integrity.py` keeps the entire repo honest by hashing every file, storing checkpoints, and repairing drift. This document explains how it works and how to operate it confidently.

## 1. Components

| File/Dir | Description |
| --- | --- |
| `scripts/project_integrity.py` | CLI tool for init/status/checkpoint/verify/repair/export |
| `.project_integrity/index.json` | Current manifest: { path, hash, size, tags, last_modified } |
| `.project_integrity/checkpoints/<stamp>.json` | Frozen snapshots of the manifest |
| `.project_integrity/backups/<stamp>/<path>` | File-level backups per checkpoint |
| `configs/integrity_policy.json` | Default settings: glob includes/excludes, hash algorithm, retention |

## 2. Workflow

1. **Initialize**: `python scripts/project_integrity.py init --reason "fresh clone"`
   - Scans repo, respects exclusions, creates `index.json`, and records checkpoint `0001`.
2. **Status**: `python scripts/project_integrity.py status`
   - Compares working tree to the manifest; outputs `added/modified/deleted` counts.
3. **Verify file(s)**: `python scripts/project_integrity.py verify playground/backend/app/models.py`
   - Hashes a single file (or glob) and prints pass/fail details.
4. **Checkpoint**: `python scripts/project_integrity.py checkpoint --tag release --reason "0.4.0"`
   - Captures new snapshot, increments counter, copies files into `.project_integrity/backups/<stamp>`.
5. **Repair**: `python scripts/project_integrity.py repair playground/backend/app/models.py --checkpoint latest`
   - Restores a file from the last (or specified) checkpoint backup.
6. **Export**: `python scripts/project_integrity.py export backups/release-0.4.0.zip --checkpoint 0007`
   - Bundles the checkpoint backup into a zip for sharing.

## 3. Metadata tracked

```jsonc
{
   "path": "playground/backend/app/models.py",
  "hash": "sha256:...",
  "size": 5123,
  "last_modified": "2025-11-15T00:21:05Z",
  "tags": ["backend", "models"],
  "version": "0.3.1",
  "milestone": "ops-overhaul",
  "notes": "Adds TailLogEntry model"
}
```

- `tags` come from the file’s banner (`# @tag:backend,models`).
- `version` / `milestone` fields are set when you pass `--tag` / `--milestone` flags to `checkpoint`.

## 4. Policies

- Hash algorithm defaults to `sha256` (change in `configs/integrity_policy.json`).
- Exclusions: `.git/`, `.venv/`, `node_modules/`, `.ipynb_checkpoints/`, `.project_integrity/`, `backups/`.
- Retention: keep the last 10 checkpoints by default, pruning older backups (configurable).

## 5. Repair strategies

| Scenario | Command |
| --- | --- |
| Single file drift | `python scripts/project_integrity.py repair path/to/file` |
| Directory drift | `python scripts/project_integrity.py repair playground/backend --checkpoint 0005` |
| Full reset | `python scripts/project_integrity.py repair --all --checkpoint latest` |

If a file no longer exists in the checkpoint, the tool aborts with instructions to restore manually.

## 6. Integration points

- **Ops Deck**: tag Ops commands with checkpoint IDs for audit logs.
- **DataLab notebooks**: include the checkpoint ID in notebook metadata when publishing results.
- **CI future work**: integrate `status` checks into GitHub Actions before merging.

## 7. Best practices

1. Check `status` before and after major refactors.
2. Always supply `--reason` when creating checkpoints; the manifest stores it for future archaeology.
3. When adding new directories, update `configs/integrity_policy.json` and `docs/FILE_SYSTEM.md`.
4. Use `--tags` filtering to scope status/verify output (e.g., `--tags backend,api`).

With these rules, you can detect unintended drift quickly, repair individual files, and ship verifiable releases with minimal overhead.
