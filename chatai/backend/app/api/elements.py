from __future__ import annotations

"""API surface for the Elements graph & execution service."""

# @tag:backend,api,elements

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db_session
from ..models import ElementGraph, ElementRun
from ..schemas import (
    GraphCreateRequest,
    GraphRead,
    GraphRunRead,
    GraphRunRequest,
    GraphUpdateRequest,
)
from ..services.elements import GraphExecutor, GraphValidationError, get_graph_executor

router = APIRouter(prefix="/elements", tags=["elements"])


def _graph_to_schema(row: ElementGraph) -> GraphRead:
    payload = GraphCreateRequest.model_validate(row.definition)
    return GraphRead(
        id=row.id,
        name=row.name,
        tenant_id=row.tenant_id,
        workspace_id=row.workspace_id,
        nodes=payload.nodes,
        edges=payload.edges,
        metadata=payload.metadata,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_to_schema(row: ElementRun) -> GraphRunRead:
    payload = row.result_json or {}
    return GraphRunRead(
        id=row.id,
        graph_id=row.graph_id,
        status=row.status,
        created_at=row.created_at,
        completed_at=row.completed_at,
        outputs=payload.get("outputs", {}),
        trace=payload.get("trace", []),
        error=row.error,
    )


@router.get("/graphs", response_model=list[GraphRead])
def list_graphs(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    workspace_id: str | None = Query(default=None, alias="workspaceId"),
    session: Session = Depends(get_db_session),
):
    query = session.query(ElementGraph)
    if tenant_id:
        query = query.filter(ElementGraph.tenant_id == tenant_id)
    if workspace_id:
        query = query.filter(ElementGraph.workspace_id == workspace_id)
    graphs = query.order_by(ElementGraph.updated_at.desc()).all()
    return [_graph_to_schema(graph) for graph in graphs]


@router.post("/graphs", response_model=GraphRead, status_code=status.HTTP_201_CREATED)
def create_graph(
    payload: GraphCreateRequest,
    session: Session = Depends(get_db_session),
):
    graph = ElementGraph(
        name=payload.name,
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        definition=payload.model_dump(by_alias=True),
    )
    session.add(graph)
    session.commit()
    session.refresh(graph)
    return _graph_to_schema(graph)


@router.get("/graphs/{graph_id}", response_model=GraphRead)
def get_graph(graph_id: str, session: Session = Depends(get_db_session)):
    graph = session.get(ElementGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    return _graph_to_schema(graph)


@router.put("/graphs/{graph_id}", response_model=GraphRead)
def update_graph(
    graph_id: str,
    payload: GraphUpdateRequest,
    session: Session = Depends(get_db_session),
):
    graph = session.get(ElementGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    graph.name = payload.name
    graph.tenant_id = payload.tenant_id
    graph.workspace_id = payload.workspace_id
    graph.definition = payload.model_dump(by_alias=True)
    graph.updated_at = datetime.now(timezone.utc)
    session.add(graph)
    session.commit()
    session.refresh(graph)
    return _graph_to_schema(graph)


@router.delete("/graphs/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_graph(graph_id: str, session: Session = Depends(get_db_session)):
    graph = session.get(ElementGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    session.query(ElementRun).filter(ElementRun.graph_id == graph_id).delete()
    session.delete(graph)
    session.commit()
    return None


@router.post("/graphs/{graph_id}:execute", response_model=GraphRunRead, status_code=status.HTTP_202_ACCEPTED)
def execute_graph(
    graph_id: str,
    payload: GraphRunRequest,
    session: Session = Depends(get_db_session),
    executor: GraphExecutor = Depends(get_graph_executor),
):
    graph = session.get(ElementGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    graph_schema = _graph_to_schema(graph)
    overrides = {node_id: override.props for node_id, override in payload.overrides.items()}
    try:
        result = executor.execute(graph_schema, overrides=overrides)
    except GraphValidationError as exc:  # pragma: no cover - handled via FastAPI response
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    run = ElementRun(
        graph_id=graph.id,
        status=result.status,
        result_json={"outputs": result.outputs, "trace": result.trace},
        error=result.error,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_to_schema(run)


@router.get("/runs/{run_id}", response_model=GraphRunRead)
def get_run(run_id: str, session: Session = Depends(get_db_session)):
    run = session.get(ElementRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _run_to_schema(run)
