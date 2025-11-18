from __future__ import annotations

"""Element graph persistence across SQLite and Azure Cosmos DB."""

# @tag: backend,repositories,elements

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional, Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import ElementGraph, ElementRun
from ..schemas import (
    GraphCreateRequest,
    GraphRead,
    GraphRunRead,
    GraphRunStatus,
    GraphUpdateRequest,
)
from ..services.elements import GraphExecutionResult

try:  # pragma: no cover - optional dependency for Cosmos workloads
    from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exceptions
    from azure.identity import DefaultAzureCredential
except ImportError:  # pragma: no cover
    CosmosClient = None  # type: ignore
    PartitionKey = None  # type: ignore
    cosmos_exceptions = None  # type: ignore
    DefaultAzureCredential = None  # type: ignore


@dataclass
class GraphFilter:
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None


class ElementGraphRepository(Protocol):
    """Storage contract for graph definitions and execution runs."""

    def list_graphs(self, filters: GraphFilter) -> list[GraphRead]:
        ...

    def create_graph(self, payload: GraphCreateRequest) -> GraphRead:
        ...

    def get_graph(self, graph_id: str) -> GraphRead | None:
        ...

    def update_graph(self, graph_id: str, payload: GraphUpdateRequest) -> GraphRead:
        ...

    def delete_graph(self, graph_id: str) -> None:
        ...

    def get_run(self, run_id: str) -> GraphRunRead | None:
        ...

    def delete_runs_for_graph(self, graph_id: str) -> None:
        ...

    def create_run(self, graph: GraphRead, status: GraphRunStatus = "queued") -> GraphRunRead:
        ...

    def update_run(
        self,
        run_id: str,
        *,
        status: GraphRunStatus,
        result: GraphExecutionResult | None = None,
        error: str | None = None,
    ) -> GraphRunRead:
        ...

    def count_active_runs(self, tenant_id: str, workspace_id: str) -> int:
        ...

    def list_runs(self, graph_id: str, limit: int = 20) -> list[GraphRunRead]:
        ...


# --- SQLAlchemy implementation -------------------------------------------------
class SqlElementGraphRepository:
    """SQL-backed repository used for local dev and CI."""

    def __init__(self, session: Session):
        self._session = session

    def list_graphs(self, filters: GraphFilter) -> list[GraphRead]:
        query = self._session.query(ElementGraph)
        if filters.tenant_id:
            query = query.filter(ElementGraph.tenant_id == filters.tenant_id)
        if filters.workspace_id:
            query = query.filter(ElementGraph.workspace_id == filters.workspace_id)
        graphs = query.order_by(ElementGraph.updated_at.desc()).all()
        return [_row_to_graph(graph) for graph in graphs]

    def create_graph(self, payload: GraphCreateRequest) -> GraphRead:
        graph = ElementGraph(
            name=payload.name,
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            definition=payload.model_dump(by_alias=True),
        )
        self._session.add(graph)
        self._session.commit()
        self._session.refresh(graph)
        return _row_to_graph(graph)

    def get_graph(self, graph_id: str) -> GraphRead | None:
        graph = self._session.get(ElementGraph, graph_id)
        return _row_to_graph(graph) if graph else None

    def update_graph(self, graph_id: str, payload: GraphUpdateRequest) -> GraphRead:
        graph = self._session.get(ElementGraph, graph_id)
        if not graph:
            raise LookupError("Graph not found")
        graph.name = payload.name
        graph.tenant_id = payload.tenant_id
        graph.workspace_id = payload.workspace_id
        graph.definition = payload.model_dump(by_alias=True)
        graph.updated_at = datetime.now(timezone.utc)
        self._session.add(graph)
        self._session.commit()
        self._session.refresh(graph)
        return _row_to_graph(graph)

    def delete_graph(self, graph_id: str) -> None:
        graph = self._session.get(ElementGraph, graph_id)
        if not graph:
            return
        self._session.query(ElementRun).filter(ElementRun.graph_id == graph_id).delete()
        self._session.delete(graph)
        self._session.commit()

    def get_run(self, run_id: str) -> GraphRunRead | None:
        run = self._session.get(ElementRun, run_id)
        return _row_to_run(run) if run else None

    def delete_runs_for_graph(self, graph_id: str) -> None:
        self._session.query(ElementRun).filter(ElementRun.graph_id == graph_id).delete()
        self._session.commit()

    def create_run(self, graph: GraphRead, status: GraphRunStatus = "queued") -> GraphRunRead:
        run = ElementRun(
            graph_id=graph.id,
            status=status,
            result_json={"outputs": {}, "trace": []},
            error=None,
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return _row_to_run(run)

    def update_run(
        self,
        run_id: str,
        *,
        status: GraphRunStatus,
        result: GraphExecutionResult | None = None,
        error: str | None = None,
    ) -> GraphRunRead:
        run = self._session.get(ElementRun, run_id)
        if not run:
            raise LookupError("Run not found")
        run.status = status
        if result is not None:
            run.result_json = {"outputs": result.outputs, "trace": result.trace}
            run.error = result.error
        if error is not None:
            run.error = error
        if status in ("succeeded", "failed"):
            run.completed_at = datetime.now(timezone.utc)
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return _row_to_run(run)

    def count_active_runs(self, tenant_id: str, workspace_id: str) -> int:
        query = (
            self._session.query(ElementRun)
            .join(ElementGraph, ElementGraph.id == ElementRun.graph_id)
            .filter(ElementGraph.tenant_id == tenant_id, ElementGraph.workspace_id == workspace_id)
            .filter(ElementRun.status.in_(["queued", "running"]))
        )
        return query.count()

    def list_runs(self, graph_id: str, limit: int = 20) -> list[GraphRunRead]:
        runs = (
            self._session.query(ElementRun)
            .filter(ElementRun.graph_id == graph_id)
            .order_by(ElementRun.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_run(run) for run in runs]


# --- Cosmos DB implementation --------------------------------------------------
class CosmosElementGraphRepository:
    """Cosmos-backed repository with hierarchical partition keys."""

    def __init__(self, settings: Settings):
        if CosmosClient is None:
            raise RuntimeError("azure-cosmos is required for Cosmos repositories")
        if not settings.cosmos_enabled:
            raise RuntimeError("Cosmos settings are not configured")

        self._settings = settings
        self._client = _get_cosmos_client(settings)
        self._database = self._client.create_database_if_not_exists(id=settings.cosmos_database)
        self._graph_container = self._database.create_container_if_not_exists(
            id=settings.cosmos_graph_container,
            partition_key=PartitionKey(path=["/tenantId", "/workspaceId"]),
        )
        self._run_container = self._database.create_container_if_not_exists(
            id=settings.cosmos_run_container,
            partition_key=PartitionKey(path="/graphId"),
        )

    def list_graphs(self, filters: GraphFilter) -> list[GraphRead]:
        clauses: list[str] = []
        parameters: list[dict[str, str]] = []
        if filters.tenant_id:
            clauses.append("c.tenantId = @tenantId")
            parameters.append({"name": "@tenantId", "value": filters.tenant_id})
        if filters.workspace_id:
            clauses.append("c.workspaceId = @workspaceId")
            parameters.append({"name": "@workspaceId", "value": filters.workspace_id})
        query = "SELECT * FROM c"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY c.updatedAt DESC"
        items = self._graph_container.query_items(
            query=query,
            parameters=parameters or None,
            enable_cross_partition_query=True,
        )
        return [_doc_to_graph(doc) for doc in items]

    def create_graph(self, payload: GraphCreateRequest) -> GraphRead:
        graph_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": graph_id,
            "graphId": graph_id,
            "tenantId": payload.tenant_id,
            "workspaceId": payload.workspace_id,
            "name": payload.name,
            "definition": payload.model_dump(by_alias=True),
            "metadata": payload.metadata.model_dump(by_alias=True) if payload.metadata else None,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        self._graph_container.create_item(doc)
        return _doc_to_graph(doc)

    def get_graph(self, graph_id: str) -> GraphRead | None:
        doc = self._fetch_graph_doc(graph_id)
        return _doc_to_graph(doc) if doc else None

    def update_graph(self, graph_id: str, payload: GraphUpdateRequest) -> GraphRead:
        doc = self.get_graph(graph_id)
        if not doc:
            raise LookupError("Graph not found")
        timestamp = datetime.now(timezone.utc).isoformat()
        updated_doc = {
            "id": graph_id,
            "graphId": graph_id,
            "tenantId": payload.tenant_id,
            "workspaceId": payload.workspace_id,
            "name": payload.name,
            "definition": payload.model_dump(by_alias=True),
            "metadata": payload.metadata.model_dump(by_alias=True) if payload.metadata else None,
            "createdAt": doc.created_at.isoformat(),
            "updatedAt": timestamp,
        }
        self._graph_container.replace_item(item=graph_id, body=updated_doc, partition_key=self._graph_partition_key(payload))
        return _doc_to_graph(updated_doc)

    def delete_graph(self, graph_id: str) -> None:
        graph = self.get_graph(graph_id)
        if not graph:
            return
        self.delete_runs_for_graph(graph_id)
        partition_key = self._graph_partition_key(graph)
        self._graph_container.delete_item(item=graph_id, partition_key=partition_key)

    def get_run(self, run_id: str) -> GraphRunRead | None:
        doc = self._fetch_run_doc(run_id)
        return _doc_to_run(doc) if doc else None

    def delete_runs_for_graph(self, graph_id: str) -> None:
        query = "SELECT c.id FROM c WHERE c.graphId = @graphId"
        params = [{"name": "@graphId", "value": graph_id}]
        items = self._run_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=False,
        )
        for item in items:
            self._run_container.delete_item(item=item["id"], partition_key=graph_id)

    def create_run(self, graph: GraphRead, status: GraphRunStatus = "queued") -> GraphRunRead:
        run_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": run_id,
            "runId": run_id,
            "graphId": graph.id,
            "tenantId": graph.tenant_id,
            "workspaceId": graph.workspace_id,
            "status": status,
            "outputs": {},
            "trace": [],
            "error": None,
            "createdAt": created_at,
            "completedAt": None,
        }
        self._run_container.create_item(doc)
        return _doc_to_run(doc)

    def update_run(
        self,
        run_id: str,
        *,
        status: GraphRunStatus,
        result: GraphExecutionResult | None = None,
        error: str | None = None,
    ) -> GraphRunRead:
        doc = self._fetch_run_doc(run_id)
        if not doc:
            raise LookupError("Run not found")
        doc["status"] = status
        if result is not None:
            doc["outputs"] = result.outputs
            doc["trace"] = result.trace
            doc["error"] = result.error
        if error is not None:
            doc["error"] = error
        if status in ("succeeded", "failed"):
            doc["completedAt"] = datetime.now(timezone.utc).isoformat()
        self._run_container.replace_item(item=doc["id"], partition_key=doc["graphId"], body=doc)
        return _doc_to_run(doc)

    def count_active_runs(self, tenant_id: str, workspace_id: str) -> int:
        query = (
            "SELECT VALUE COUNT(1) FROM c WHERE c.tenantId = @tenantId "
            "AND c.workspaceId = @workspaceId AND (c.status = 'queued' OR c.status = 'running')"
        )
        params = [
            {"name": "@tenantId", "value": tenant_id},
            {"name": "@workspaceId", "value": workspace_id},
        ]
        items = list(
            self._run_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else 0

    def list_runs(self, graph_id: str, limit: int = 20) -> list[GraphRunRead]:
        query = "SELECT * FROM c WHERE c.graphId = @graphId ORDER BY c.createdAt DESC"
        params = [{"name": "@graphId", "value": graph_id}]
        items = self._run_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=False,
        )
        runs: list[GraphRunRead] = []
        for doc in items:
            runs.append(_doc_to_run(doc))
            if len(runs) >= limit:
                break
        return runs

    def _graph_partition_key(self, graph: GraphRead | GraphUpdateRequest) -> list[str]:
        return [graph.tenant_id, graph.workspace_id]

    def _fetch_graph_doc(self, graph_id: str) -> dict | None:
        query = "SELECT * FROM c WHERE c.id = @graphId"
        params = [{"name": "@graphId", "value": graph_id}]
        items = list(
            self._graph_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else None

    def _fetch_run_doc(self, run_id: str) -> dict | None:
        query = "SELECT * FROM c WHERE c.id = @runId"
        params = [{"name": "@runId", "value": run_id}]
        items = list(
            self._run_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else None


# --- Helpers ------------------------------------------------------------------
def _row_to_graph(row: ElementGraph) -> GraphRead:
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


def _row_to_run(row: ElementRun) -> GraphRunRead:
    payload = row.result_json or {}
    return GraphRunRead(
        id=row.id,
        graph_id=row.graph_id,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        completed_at=row.completed_at,
        outputs=payload.get("outputs", {}),
        trace=payload.get("trace", []),
        error=row.error,
    )


def _doc_to_graph(doc: dict) -> GraphRead:
    definition = doc["definition"]
    payload = GraphCreateRequest.model_validate(definition)
    return GraphRead(
        id=doc["graphId"],
        name=doc["name"],
        tenant_id=doc["tenantId"],
        workspace_id=doc["workspaceId"],
        nodes=payload.nodes,
        edges=payload.edges,
        metadata=payload.metadata,
        created_at=datetime.fromisoformat(doc["createdAt"]),
        updated_at=datetime.fromisoformat(doc["updatedAt"]),
    )


def _doc_to_run(doc: dict) -> GraphRunRead:
    completed_at = doc.get("completedAt")
    return GraphRunRead(
        id=doc["runId"],
        graph_id=doc["graphId"],
        status=doc.get("status", "succeeded"),  # type: ignore[arg-type]
        created_at=datetime.fromisoformat(doc["createdAt"]),
        completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
        outputs=doc.get("outputs", {}),
        trace=doc.get("trace", []),
        error=doc.get("error"),
    )


def _get_cosmos_client(settings: Settings) -> CosmosClient:
    cache_key = "cosmos_client"

    @lru_cache(maxsize=1)
    def _build(_: str) -> CosmosClient:
        if settings.cosmos_key:
            credential = settings.cosmos_key
        elif settings.cosmos_prefer_managed_identity:
            if DefaultAzureCredential is None:
                raise RuntimeError("azure-identity is required for managed identity authentication")
            credential = DefaultAzureCredential()
        else:
            raise RuntimeError("COSMOS_KEY must be provided when managed identity is disabled")

        return CosmosClient(
            url=settings.cosmos_endpoint,
            credential=credential,
            consistency_level=settings.cosmos_consistency,
        )

    return _build(cache_key)


# --- Dependency factory -------------------------------------------------------
def get_graph_repository(
    session: Session | None = None,
    settings: Settings | None = None,
) -> ElementGraphRepository:
    resolved_settings = settings or get_settings()
    if resolved_settings.cosmos_enabled:
        return CosmosElementGraphRepository(resolved_settings)
    if session is None:
        raise RuntimeError("Database session required for SQL repository access")
    return SqlElementGraphRepository(session)
