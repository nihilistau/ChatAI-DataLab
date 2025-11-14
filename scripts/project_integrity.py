"""Integrity toolkit for the ChatAI · DataLab repository.

# @tag: scripts,integrity,tooling

Usage examples::

    python scripts/project_integrity.py init --reason "fresh clone"
    python scripts/project_integrity.py status --tags backend
    python scripts/project_integrity.py checkpoint --tag release --reason "0.4.0"
    python scripts/project_integrity.py verify chatai/backend/app/models.py
    python scripts/project_integrity.py repair chatai/backend/app/models.py --checkpoint latest
    python scripts/project_integrity.py export backups/release.zip --checkpoint 0007

The tool tracks hashes for every file (respecting inclusion/exclusion globs),
records checkpoints, copies backups, and lets you repair drift on a file-by-file basis.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Mapping
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"
POLICY_FILE = CONFIG_DIR / "integrity_policy.json"
TAGS_FILE = CONFIG_DIR / "tags.json"
INTEGRITY_DIR = ROOT / ".project_integrity"
MANIFEST_PATH = INTEGRITY_DIR / "index.json"
CHECKPOINT_DIR = INTEGRITY_DIR / "checkpoints"
BACKUP_DIR = INTEGRITY_DIR / "backups"
DEFAULT_POLICY = {
    "hash_algorithm": "sha256",
    "retain_checkpoints": 10,
    "backup_root": str(BACKUP_DIR.relative_to(ROOT)),
    "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
    "checkpoint_dir": str(CHECKPOINT_DIR.relative_to(ROOT)),
    "include_globs": ["**/*"],
    "exclude_globs": [
        ".git/**",
        "**/.venv/**",
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/.ipynb_checkpoints/**",
        ".project_integrity/**",
        "backups/**",
        "**/*.pyc",
    ],
    "default_tags": ["integrity"],
    "default_milestone": "rolling",
}


@dataclass
class FileRecord:
    path: str
    hash: str
    size: int
    last_modified: str
    tags: list[str]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "hash": self.hash,
            "size": self.size,
            "last_modified": self.last_modified,
            "tags": self.tags,
        }


class IntegrityManager:
    def __init__(self) -> None:
        self.root = ROOT
        self.policy = self._load_policy()
        self.tags_catalog = self._load_tag_catalog()
        INTEGRITY_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Policy + tags
    # ------------------------------------------------------------------
    def _load_policy(self) -> dict:
        if POLICY_FILE.exists():
            return json.loads(POLICY_FILE.read_text())
        return DEFAULT_POLICY

    def _load_tag_catalog(self) -> set[str]:
        if TAGS_FILE.exists():
            data = json.loads(TAGS_FILE.read_text()).get("tags", [])
            return {entry["name"] for entry in data}
        return set()

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------
    def load_manifest(self) -> dict:
        if MANIFEST_PATH.exists():
            return json.loads(MANIFEST_PATH.read_text())
        return {"meta": {}, "files": {}}

    def save_manifest(self, manifest: dict) -> None:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    # ------------------------------------------------------------------
    # Scanning + hashing
    # ------------------------------------------------------------------
    def scan_files(self) -> dict[str, FileRecord]:
        records: dict[str, FileRecord] = {}
        for path in self._iter_repo_files():
            rel = path.relative_to(self.root).as_posix()
            stats = path.stat()
            file_hash = self._hash_file(path)
            tags = self._extract_tags(path)
            records[rel] = FileRecord(
                path=rel,
                hash=file_hash,
                size=stats.st_size,
                last_modified=datetime.fromtimestamp(stats.st_mtime).isoformat(),
                tags=tags,
            )
        return records

    def _iter_repo_files(self) -> Iterator[Path]:
        include_patterns = self.policy.get("include_globs", ["**/*"])
        exclude_patterns = self.policy.get("exclude_globs", [])
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.root).as_posix()
            if not self._match_patterns(rel, include_patterns, default=True):
                continue
            if self._match_patterns(rel, exclude_patterns, default=False):
                continue
            yield path

    def _match_patterns(self, rel_path: str, patterns: Iterable[str], *, default: bool) -> bool:
        if not patterns:
            return default
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)

    def _hash_file(self, path: Path) -> str:
        algo = self.policy.get("hash_algorithm", "sha256")
        hasher = hashlib.new(algo)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return f"{algo}:{hasher.hexdigest()}"

    def _extract_tags(self, path: Path) -> list[str]:
        max_bytes = 4096
        tags: list[str] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                chunk = handle.read(max_bytes)
        except UnicodeDecodeError:
            return []
        for line in chunk.splitlines():
            marker = "@tag:"
            if marker in line:
                tail = line.split(marker, 1)[1]
                found = [tag.strip().lower() for tag in tail.replace("|", ",").split(",")]
                for tag in found:
                    if not tag:
                        continue
                    tags.append(tag)
        if not tags:
            tags = list(self.policy.get("default_tags", []))
        else:
            tags = [tag for tag in tags if not self.tags_catalog or tag in self.tags_catalog]
        return sorted(set(tags))

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------
    def _next_checkpoint_id(self) -> str:
        existing = sorted(p.stem for p in CHECKPOINT_DIR.glob("*.json"))
        if not existing:
            return "0001"
        return f"{int(existing[-1]) + 1:04d}"

    def _resolve_checkpoint_id(self, requested: str | None) -> str:
        if requested in (None, "latest"):
            existing = sorted(p.stem for p in CHECKPOINT_DIR.glob("*.json"))
            if not existing:
                raise RuntimeError("No checkpoints available")
            return existing[-1]
        checkpoint_path = CHECKPOINT_DIR / f"{requested}.json"
        if not checkpoint_path.exists():
            raise RuntimeError(f"Checkpoint {requested} not found")
        return requested

    def write_checkpoint(
        self,
        checkpoint_id: str,
        manifest: Mapping,
        *,
        tag: str | None,
        milestone: str | None,
        reason: str | None,
    ) -> None:
        payload = {
            "meta": {
                "checkpoint_id": checkpoint_id,
                "tag": tag,
                "milestone": milestone or self.policy.get("default_milestone"),
                "reason": reason,
                "created_at": datetime.utcnow().isoformat(),
            },
            "files": manifest["files"],
        }
        (CHECKPOINT_DIR / f"{checkpoint_id}.json").write_text(json.dumps(payload, indent=2))
        self._write_backup(checkpoint_id, manifest)
        self._prune_old_checkpoints()

    def _write_backup(self, checkpoint_id: str, manifest: Mapping) -> None:
        backup_root = BACKUP_DIR / checkpoint_id
        if backup_root.exists():
            shutil.rmtree(backup_root)
        for file_path in manifest["files"].keys():
            source = self.root / file_path
            target = backup_root / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                shutil.copy2(source, target)

    def _prune_old_checkpoints(self) -> None:
        retain = self.policy.get("retain_checkpoints", 10)
        checkpoints = sorted(CHECKPOINT_DIR.glob("*.json"))
        if len(checkpoints) <= retain:
            return
        to_remove = checkpoints[: len(checkpoints) - retain]
        for path in to_remove:
            backup = BACKUP_DIR / path.stem
            if backup.exists():
                shutil.rmtree(backup)
            path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def cmd_init(self, *, reason: str | None) -> None:
        manifest = {
            "meta": {
                "created_at": datetime.utcnow().isoformat(),
                "policy": self.policy,
                "reason": reason,
            },
            "files": {rec.path: rec.to_dict() for rec in self.scan_files().values()},
        }
        checkpoint_id = self._next_checkpoint_id()
        manifest["meta"]["checkpoint_id"] = checkpoint_id
        self.save_manifest(manifest)
        self.write_checkpoint(checkpoint_id, manifest, tag=None, milestone=None, reason=reason)
        print(f"Initialized manifest with checkpoint {checkpoint_id}")

    def cmd_status(self, *, tags: list[str] | None) -> None:
        manifest = self.load_manifest()
        if not manifest["files"]:
            print("Manifest empty. Run init first.")
            return
        current = {rec.path: rec for rec in self.scan_files().values()}
        added = sorted(set(current) - set(manifest["files"]))
        deleted = sorted(set(manifest["files"]) - set(current))
        modified = [
            path
            for path in current.keys() & manifest["files"].keys()
            if current[path].hash != manifest["files"][path]["hash"]
        ]
        if tags:
            tags_set = set(tags)
            added = [p for p in added if tags_set & set(current[p].tags)]
            deleted = [p for p in deleted if tags_set & set(manifest["files"][p]["tags"])]
            modified = [p for p in modified if tags_set & set(manifest["files"][p]["tags"])]
        summary = {
            "added": len(added),
            "deleted": len(deleted),
            "modified": len(modified),
        }
        print(json.dumps(summary, indent=2))
        for label, paths in ("added", added), ("deleted", deleted), ("modified", modified):
            if not paths:
                continue
            print(f"\n{label.upper()} ({len(paths)}):")
            for path in paths:
                print(f"  - {path}")

    def cmd_checkpoint(self, *, tag: str | None, milestone: str | None, reason: str | None) -> None:
        manifest = self.load_manifest()
        if not manifest["files"]:
            raise RuntimeError("Manifest empty. Run init first.")
        snapshot = {rec.path: rec.to_dict() for rec in self.scan_files().values()}
        manifest["files"] = snapshot
        checkpoint_id = self._next_checkpoint_id()
        manifest["meta"].update(
            {
                "checkpoint_id": checkpoint_id,
                "updated_at": datetime.utcnow().isoformat(),
                "reason": reason,
                "tag": tag,
                "milestone": milestone or self.policy.get("default_milestone"),
            }
        )
        self.save_manifest(manifest)
        self.write_checkpoint(checkpoint_id, manifest, tag=tag, milestone=milestone, reason=reason)
        print(f"Checkpoint {checkpoint_id} created")

    def cmd_verify(self, paths: list[str]) -> None:
        manifest = self.load_manifest()
        if not manifest["files"]:
            raise RuntimeError("Manifest empty. Run init first.")
        overall_ok = True
        for path in paths:
            rel = Path(path)
            if rel.is_absolute():
                rel = rel.relative_to(self.root)
            rel_str = rel.as_posix()
            if rel_str not in manifest["files"]:
                print(f"[MISSING IN MANIFEST] {rel_str}")
                overall_ok = False
                continue
            full = self.root / rel_str
            if not full.exists():
                print(f"[MISSING ON DISK] {rel_str}")
                overall_ok = False
                continue
            current_hash = self._hash_file(full)
            expected_hash = manifest["files"][rel_str]["hash"]
            if current_hash == expected_hash:
                print(f"[OK] {rel_str}")
            else:
                print(f"[DIFF] {rel_str}\n  expected={expected_hash}\n  actual={current_hash}")
                overall_ok = False
        if not overall_ok:
            sys.exit(2)

    def cmd_repair(self, targets: list[str] | None, *, checkpoint: str | None, all_files: bool) -> None:
        checkpoint_id = self._resolve_checkpoint_id(checkpoint)
        backup_root = BACKUP_DIR / checkpoint_id
        if not backup_root.exists():
            raise RuntimeError(f"Backup for checkpoint {checkpoint_id} missing")
        if all_files:
            print(f"Restoring full backup {checkpoint_id}")
            shutil.copytree(backup_root, self.root, dirs_exist_ok=True)
            return
        if not targets:
            raise RuntimeError("Provide file paths or use --all")
        for target in targets:
            rel = Path(target)
            if rel.is_absolute():
                rel = rel.relative_to(self.root)
            source = backup_root / rel
            dest = self.root / rel
            if not source.exists():
                print(f"[SKIP] {rel.as_posix()} not in checkpoint {checkpoint_id}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            print(f"[RESTORED] {rel.as_posix()} from {checkpoint_id}")

    def cmd_export(self, *, output: Path, checkpoint: str | None) -> None:
        checkpoint_id = self._resolve_checkpoint_id(checkpoint)
        checkpoint_root = BACKUP_DIR / checkpoint_id
        if not checkpoint_root.exists():
            raise RuntimeError(f"Backup folder missing for checkpoint {checkpoint_id}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in checkpoint_root.rglob("*"):
                if path.is_file():
                    arcname = Path(checkpoint_id) / path.relative_to(checkpoint_root)
                    archive.write(path, arcname.as_posix())
        print(f"Exported {checkpoint_id} → {output}")


# --------------------------------------------------------------------------
# CLI parsing
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hash + integrity toolkit for ChatAI · DataLab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python scripts/project_integrity.py init --reason "fresh clone"
              python scripts/project_integrity.py status --tags backend,ui
              python scripts/project_integrity.py checkpoint --tag release --reason "0.5.0"
              python scripts/project_integrity.py verify chatai/backend/app/models.py
              python scripts/project_integrity.py repair chatai/backend/app/models.py --checkpoint latest
              python scripts/project_integrity.py export backups/release.zip --checkpoint 0007
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create the initial manifest + checkpoint")
    init_cmd.add_argument("--reason", default=None)

    status_cmd = sub.add_parser("status", help="Show diff between disk and manifest")
    status_cmd.add_argument("--tags", default=None, help="Comma-separated tag filters")

    checkpoint_cmd = sub.add_parser("checkpoint", help="Create a new checkpoint + backup")
    checkpoint_cmd.add_argument("--tag", default=None)
    checkpoint_cmd.add_argument("--milestone", default=None)
    checkpoint_cmd.add_argument("--reason", default=None)

    verify_cmd = sub.add_parser("verify", help="Verify hashes for specific files")
    verify_cmd.add_argument("paths", nargs="+", help="Files to verify")

    repair_cmd = sub.add_parser("repair", help="Restore files from a checkpoint")
    repair_cmd.add_argument("paths", nargs="*", help="Files to repair (omit with --all)")
    repair_cmd.add_argument("--checkpoint", default=None)
    repair_cmd.add_argument("--all", action="store_true", help="Restore entire repo")

    export_cmd = sub.add_parser("export", help="Zip a checkpoint backup")
    export_cmd.add_argument("output", help="Destination zip path")
    export_cmd.add_argument("--checkpoint", default=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    manager = IntegrityManager()

    if args.command == "init":
        manager.cmd_init(reason=args.reason)
    elif args.command == "status":
        tags = args.tags.split(",") if args.tags else None
        manager.cmd_status(tags=tags)
    elif args.command == "checkpoint":
        manager.cmd_checkpoint(tag=args.tag, milestone=args.milestone, reason=args.reason)
    elif args.command == "verify":
        manager.cmd_verify(args.paths)
    elif args.command == "repair":
        manager.cmd_repair(args.paths, checkpoint=args.checkpoint, all_files=args.all)
    elif args.command == "export":
        manager.cmd_export(output=Path(args.output), checkpoint=args.checkpoint)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
