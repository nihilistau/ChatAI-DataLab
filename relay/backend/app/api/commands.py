from __future__ import annotations

"""API surface for persistent LabControl commands."""

# @tag:backend,api,commands

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import (
    CommandStatus,
    CommandCreateRequest,
    CommandExecutionRead,
    CommandRecord,
    CommandRunRequest,
)
from ..services.command_store import CommandEntry, CommandStore, get_command_store

router = APIRouter(prefix="/commands", tags=["commands"])


def _to_response(entry: CommandEntry) -> CommandRecord:
    return CommandRecord(
        id=entry.id,
        label=entry.label,
        command=entry.command,
        created_at=entry.created_at,
        added_by=entry.added_by,
        tags=entry.tags,
        description=entry.description,
        working_dir=entry.working_dir,
        last_status=entry.last_status,
        last_run_at=entry.last_run_at,
        history=[
            CommandExecutionRead(
                timestamp=record.timestamp,
                status=record.status,
                exit_code=record.exit_code,
                output=record.output,
                notes=record.notes,
                failed=record.failed,
                command=record.command,
            )
            for record in entry.history
        ],
    )


def get_store_dep() -> CommandStore:
    return get_command_store()


@router.get("", response_model=list[CommandRecord])
def list_commands(
    status: CommandStatus | None = Query(default=None, description="Filter by last_status"),
    tag: str | None = Query(default=None, min_length=1, description="Require commands tagged with this value"),
    limit: int | None = Query(default=None, ge=1, le=500, description="Return only the N most recent commands"),
    store: CommandStore = Depends(get_store_dep),
) -> list[CommandRecord]:
    entries = store.list_commands()
    if status:
        entries = [entry for entry in entries if entry.last_status == status]
    if tag:
        lowered = tag.lower()
        entries = [entry for entry in entries if any(t.lower() == lowered for t in entry.tags)]
    if limit is not None:
        entries = entries[-limit:]
    return [_to_response(entry) for entry in entries]


@router.get("/{command_id}", response_model=CommandRecord)
def get_command(command_id: str, store: CommandStore = Depends(get_store_dep)) -> CommandRecord:
    try:
        entry = store.get_command(command_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(entry)


@router.post("", response_model=CommandRecord, status_code=status.HTTP_201_CREATED)
def create_command(payload: CommandCreateRequest, store: CommandStore = Depends(get_store_dep)) -> CommandRecord:
    entry = store.add_command(
        label=payload.label,
        command=payload.command,
        added_by=payload.added_by,
        tags=payload.tags,
        description=payload.description,
        working_dir=payload.working_dir,
    )
    return _to_response(entry)


@router.post("/{command_id}/run", response_model=CommandRecord)
def run_command(
    command_id: str,
    payload: CommandRunRequest,
    store: CommandStore = Depends(get_store_dep),
) -> CommandRecord:
    try:
        entry = store.run_command(command_id, dry_run=payload.dry_run, shell=payload.shell)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return _to_response(entry)


@router.get("/{command_id}/history", response_model=list[CommandExecutionRead])
def get_command_history(
    command_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Maximum records to return"),
    status: CommandStatus | None = Query(default=None, description="Optional status filter applied to history entries"),
    store: CommandStore = Depends(get_store_dep),
) -> list[CommandExecutionRead]:
    try:
        entry = store.get_command(command_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    history = entry.history
    if status:
        history = [record for record in history if record.status == status]
    history = history[-limit:]
    return [
        CommandExecutionRead(
            timestamp=record.timestamp,
            status=record.status,
            exit_code=record.exit_code,
            output=record.output,
            notes=record.notes,
            failed=record.failed,
            command=record.command,
        )
        for record in history
    ]