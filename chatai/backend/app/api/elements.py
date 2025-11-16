from __future__ import annotations

"""API surface for the Elements graph & execution service."""

# @tag:backend,api,elements

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db_session
from ..repositories.elements import GraphFilter, ElementGraphRepository, get_graph_repository
from ..schemas import (
    GraphCreateRequest,
    GraphRead,
    GraphRunRead,
    GraphRunRequest,
    GraphUpdateRequest,
)
from ..services.graph_runs import GraphRunDispatcher, get_graph_run_dispatcher

router = APIRouter(prefix="/elements", tags=["elements"])


def get_graph_repository_dependency(
    session: Session = Depends(get_db_session),
) -> ElementGraphRepository:
    return get_graph_repository(session=session)


def get_settings_dependency() -> Settings:
    return get_settings()


def get_graph_run_dispatcher_dependency() -> GraphRunDispatcher:
    return get_graph_run_dispatcher()


@router.get("/graphs", response_model=list[GraphRead])
def list_graphs(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    workspace_id: str | None = Query(default=None, alias="workspaceId"),
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    filters = GraphFilter(tenant_id=tenant_id, workspace_id=workspace_id)
    return repository.list_graphs(filters)


@router.post("/graphs", response_model=GraphRead, status_code=status.HTTP_201_CREATED)
def create_graph(
    payload: GraphCreateRequest,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    return repository.create_graph(payload)


@router.get("/graphs/{graph_id}", response_model=GraphRead)
def get_graph(
    graph_id: str,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    graph = repository.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    return graph


@router.put("/graphs/{graph_id}", response_model=GraphRead)
def update_graph(
    graph_id: str,
    payload: GraphUpdateRequest,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    try:
        return repository.update_graph(graph_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found") from exc


@router.delete("/graphs/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_graph(
    graph_id: str,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    graph = repository.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    repository.delete_graph(graph_id)
    return None


@router.post("/graphs/{graph_id}:execute", response_model=GraphRunRead, status_code=status.HTTP_202_ACCEPTED)
async def execute_graph(
    graph_id: str,
    payload: GraphRunRequest | None = None,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
    dispatcher: GraphRunDispatcher = Depends(get_graph_run_dispatcher_dependency),
    settings: Settings = Depends(get_settings_dependency),
):
    graph = repository.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    requested_overrides = payload.overrides if payload else {}
    overrides = {node_id: override.props for node_id, override in requested_overrides.items()}
    active_runs = repository.count_active_runs(graph.tenant_id, graph.workspace_id)
    if active_runs >= settings.elements_max_active_runs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many runs are currently active for this workspace. "
                f"Limit: {settings.elements_max_active_runs}"
            ),
        )

    run = repository.create_run(graph, status="queued")
    await dispatcher.enqueue(run, graph, overrides)
    return run


@router.get("/runs/{run_id}", response_model=GraphRunRead)
def get_run(
    run_id: str,
    repository: ElementGraphRepository = Depends(get_graph_repository_dependency),
):
    run = repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run
