from __future__ import annotations

"""Persistent command store for LabControl + API usage."""
# @tag:backend,services,commands

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import shlex
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from ..config import PROJECT_ROOT


CommandStatus = Literal["never-run", "running", "succeeded", "failed"]


@dataclass
class CommandExecution:
    timestamp: datetime
    status: CommandStatus
    exit_code: int | None = None
    output: str | None = None
    notes: str | None = None
    failed: bool = False
    command: str | None = None


@dataclass
class CommandEntry:
    id: str
    label: str
    command: str
    created_at: datetime
    added_by: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    working_dir: str | None = None
    last_status: CommandStatus = "never-run"
    last_run_at: datetime | None = None
    history: list[CommandExecution] = field(default_factory=list)


class CommandStore:
    """File-backed command registry with execution helpers."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or PROJECT_ROOT / "data" / "commands.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.store_path.exists():
            self._write_raw([])

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _read_raw(self) -> list[dict[str, Any]]:
        with self._lock:
            with self.store_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)

    def _write_raw(self, payload: list[dict[str, Any]]) -> None:
        tmp_path = self.store_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, default=self._json_default, indent=2)
        os.replace(tmp_path, self.store_path)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Unsupported JSON type: {type(value)!r}")

    def _deserialize(self, data: dict[str, Any]) -> CommandEntry:
        history = [
            CommandExecution(
                timestamp=datetime.fromisoformat(item["timestamp"]),
                status=item["status"],
                exit_code=item.get("exit_code"),
                output=item.get("output"),
                notes=item.get("notes"),
                failed=item.get("failed", item.get("Failed", False)),
                command=item.get("command"),
            )
            for item in data.get("history", [])
        ]
        last_run = data.get("last_run_at")
        return CommandEntry(
            id=data["id"],
            label=data["label"],
            command=data["command"],
            created_at=datetime.fromisoformat(data["created_at"]),
            added_by=data.get("added_by"),
            tags=data.get("tags", []),
            description=data.get("description"),
            working_dir=data.get("working_dir"),
            last_status=data.get("last_status", "never-run"),
            last_run_at=datetime.fromisoformat(last_run) if last_run else None,
            history=history,
        )

    def _serialize(self, entry: CommandEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "label": entry.label,
            "command": entry.command,
            "created_at": entry.created_at,
            "added_by": entry.added_by,
            "tags": entry.tags,
            "description": entry.description,
            "working_dir": entry.working_dir,
            "last_status": entry.last_status,
            "last_run_at": entry.last_run_at,
            "history": [
                {
                    "timestamp": record.timestamp,
                    "status": record.status,
                    "exit_code": record.exit_code,
                    "output": record.output,
                    "notes": record.notes,
                    "failed": record.failed,
                    "command": record.command,
                }
                for record in entry.history
            ],
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_commands(self) -> list[CommandEntry]:
        return [self._deserialize(item) for item in self._read_raw()]

    def add_command(
        self,
        *,
        label: str,
        command: str,
        added_by: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        working_dir: str | None = None,
    ) -> CommandEntry:
        entry = CommandEntry(
            id=str(uuid.uuid4()),
            label=label,
            command=command,
            created_at=datetime.now(timezone.utc),
            added_by=added_by,
            tags=tags or [],
            description=description,
            working_dir=working_dir,
        )
        entries = self._read_raw()
        entries.append(self._serialize(entry))
        self._write_raw(entries)
        return entry

    def list_successful_commands(self) -> list[CommandEntry]:
        return [entry for entry in self.list_commands() if entry.last_status == "succeeded"]

    def get_command(self, command_id: str) -> CommandEntry:
        for entry in self.list_commands():
            if entry.id == command_id:
                return entry
        raise KeyError(f"Command '{command_id}' not found")

    def record_execution(
        self,
        command_id: str,
        *,
        status: CommandStatus,
        exit_code: int | None,
        output: str | None,
        notes: str | None = None,
        command: str | None = None,
    ) -> CommandEntry:
        entries = self.list_commands()
        updated: list[dict[str, Any]] = []
        target: CommandEntry | None = None
        for entry in entries:
            if entry.id == command_id:
                entry.history.append(
                    CommandExecution(
                        timestamp=datetime.now(timezone.utc),
                        status=status,
                        exit_code=exit_code,
                        output=output,
                        notes=notes,
                        failed=status == "failed",
                        command=command or entry.command,
                    )
                )
                entry.last_status = status
                entry.last_run_at = entry.history[-1].timestamp
                target = entry
            updated.append(self._serialize(entry))
        if target is None:
            raise KeyError(f"Command '{command_id}' not found")
        self._write_raw(updated)
        return target

    def run_command(
        self,
        command_id: str,
        *,
        dry_run: bool = False,
        shell: str | None = None,
    ) -> CommandEntry:
        entry = self.get_command(command_id)
        if dry_run:
            return self.record_execution(
                command_id,
                status="succeeded",
                exit_code=0,
                output="Dry run – command not executed",
                notes="dry-run",
                command=entry.command,
            )

        cmd = entry.command
        cwd = Path(entry.working_dir).expanduser() if entry.working_dir else PROJECT_ROOT
        cwd.mkdir(parents=True, exist_ok=True)
        chosen_shell = shell or self._default_shell()
        if chosen_shell:
            exec_cmd = [chosen_shell, "-c", cmd]
        else:
            exec_cmd = cmd if os.name == "nt" else shlex.split(cmd)
        completed = subprocess.run(
            exec_cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            shell=chosen_shell is None and os.name == "nt",
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        status: CommandStatus = "succeeded" if completed.returncode == 0 else "failed"
        return self.record_execution(
            command_id,
            status=status,
            exit_code=completed.returncode,
            output=output.strip(),
            command=entry.command,
        )

    @staticmethod
    def _default_shell() -> str | None:
        if os.name == "nt":
            return shutil.which("pwsh") or shutil.which("powershell")
        return shutil.which("bash")


_STORE: CommandStore | None = None


def get_command_store() -> CommandStore:
    global _STORE
    if _STORE is None:
        _STORE = CommandStore()
    return _STORE


def set_command_store(store: CommandStore | None) -> None:
    global _STORE
    _STORE = store