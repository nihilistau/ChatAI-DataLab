from __future__ import annotations

"""Tests for the Elements graph CRUD + execution endpoints."""

# @tag:backend,tests,elements

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient  # type: ignore[import-not-found]

from app.api import elements as elements_api
from app.config import get_settings
from app.repositories.elements import ElementGraphRepository, GraphFilter
from app.schemas import GraphRead, GraphRunRead, GraphRunStatus, GraphUpdateRequest
from app.services.elements import GraphExecutionResult
from main import app


class InMemoryElementRepository(ElementGraphRepository):
    def __init__(self) -> None:
        self.graphs: dict[str, GraphRead] = {}
        self.runs: dict[str, GraphRunRead] = {}
        self.create_calls = 0
        self.create_run_calls = 0
        self.update_run_calls = 0

    def list_graphs(self, filters: GraphFilter) -> list[GraphRead]:
        items = [
            graph
            for graph in self.graphs.values()
            if (not filters.tenant_id or graph.tenant_id == filters.tenant_id)
            and (not filters.workspace_id or graph.workspace_id == filters.workspace_id)
        ]
        return sorted(items, key=lambda graph: graph.updated_at, reverse=True)

    def create_graph(self, payload):  # type: ignore[override]
        self.create_calls += 1
        now = datetime.now(timezone.utc)
        graph = GraphRead(
            id=str(uuid4()),
            name=payload.name,
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            nodes=payload.nodes,
            edges=payload.edges,
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        self.graphs[graph.id] = graph
        return graph

    def get_graph(self, graph_id: str) -> GraphRead | None:
        return self.graphs.get(graph_id)

    def update_graph(self, graph_id: str, payload: GraphUpdateRequest) -> GraphRead:
        graph = self.graphs.get(graph_id)
        if not graph:
            raise LookupError("Graph not found")
        now = datetime.now(timezone.utc)
        updated = graph.model_copy(
            update={
                "name": payload.name,
                "tenant_id": payload.tenant_id,
                "workspace_id": payload.workspace_id,
                "nodes": payload.nodes,
                "edges": payload.edges,
                "metadata": payload.metadata,
                "updated_at": now,
            }
        )
        self.graphs[graph_id] = updated
        return updated

    def delete_graph(self, graph_id: str) -> None:
        self.graphs.pop(graph_id, None)
        self.delete_runs_for_graph(graph_id)

    def create_run(self, graph: GraphRead, status: GraphRunStatus = "queued") -> GraphRunRead:
        self.create_run_calls += 1
        now = datetime.now(timezone.utc)
        run = GraphRunRead(
            id=str(uuid4()),
            graph_id=graph.id,
            status=status,
            created_at=now,
            completed_at=None,
            outputs={},
            trace=[],
            error=None,
        )
        self.runs[run.id] = run
        return run

    def update_run(
        self,
        run_id: str,
        *,
        status: GraphRunStatus,
        result: GraphExecutionResult | None = None,
        error: str | None = None,
    ) -> GraphRunRead:
        self.update_run_calls += 1
        run = self.runs.get(run_id)
        if not run:
            raise LookupError("Run not found")
        completed_at = run.completed_at
        outputs = run.outputs
        trace = run.trace
        if result is not None:
            outputs = result.outputs
            trace = result.trace
            error = result.error
            completed_at = datetime.now(timezone.utc)
        elif status in ("succeeded", "failed"):
            completed_at = datetime.now(timezone.utc)
        updated = run.model_copy(
            update={
                "status": status,
                "outputs": outputs,
                "trace": trace,
                "error": error if error is not None else run.error,
                "completed_at": completed_at,
            }
        )
        self.runs[run_id] = updated
        return updated

    def count_active_runs(self, tenant_id: str, workspace_id: str) -> int:
        count = 0
        for run in self.runs.values():
            graph = self.graphs.get(run.graph_id)
            if not graph:
                continue
            if graph.tenant_id == tenant_id and graph.workspace_id == workspace_id and run.status in (
                "queued",
                "running",
            ):
                count += 1
        return count

    def list_runs(self, graph_id: str, limit: int = 20) -> list[GraphRunRead]:
        runs = [run for run in self.runs.values() if run.graph_id == graph_id]
        runs.sort(key=lambda run: run.created_at, reverse=True)
        return runs[:limit]

    def get_run(self, run_id: str) -> GraphRunRead | None:
        return self.runs.get(run_id)

    def delete_runs_for_graph(self, graph_id: str) -> None:
        to_delete = [run_id for run_id, run in self.runs.items() if run.graph_id == graph_id]
        for run_id in to_delete:
            self.runs.pop(run_id, None)


class DummyDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[GraphRunRead, GraphRead, dict]] = []

    async def enqueue(self, run: GraphRunRead, graph: GraphRead, overrides: dict) -> None:
        self.calls.append((run, graph, overrides))


def _graph_payload() -> dict:
    return {
        "name": "LLM QA Loop",
        "tenantId": "lab",
        "workspaceId": "default",
        "nodes": [
            {"id": "node_prompt", "type": "prompt", "label": "Prompt", "props": {"text": "Hello"}},
            {
                "id": "node_llm",
                "type": "llm",
                "label": "LLM",
                "props": {"model": "gpt-4o-mini", "temperature": 0.1},
            },
            {
                "id": "node_notebook",
                "type": "notebook",
                "label": "Notebook",
                "props": {"notebook": "control_center_playground.ipynb"},
            },
        ],
        "edges": [
            {
                "id": "edge_prompt_llm",
                "from": {"node": "node_prompt", "port": "text"},
                "to": {"node": "node_llm", "port": "prompt"},
            },
            {
                "id": "edge_llm_notebook",
                "from": {"node": "node_llm", "port": "response"},
                "to": {"node": "node_notebook", "port": "parameters"},
            },
        ],
        "metadata": {"tags": ["qa"], "createdBy": "pytest"},
    }


def test_graph_crud_flow(client: TestClient) -> None:
    create_resp = client.post("/api/elements/graphs", json=_graph_payload())
    assert create_resp.status_code == 201
    graph_id = create_resp.json()["id"]

    list_resp = client.get("/api/elements/graphs", params={"tenantId": "lab"})
    assert list_resp.status_code == 200
    assert any(graph["id"] == graph_id for graph in list_resp.json())

    update_payload = _graph_payload()
    update_payload["name"] = "Updated"
    put_resp = client.put(f"/api/elements/graphs/{graph_id}", json=update_payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Updated"

    delete_resp = client.delete(f"/api/elements/graphs/{graph_id}")
    assert delete_resp.status_code == 204


def test_execute_graph_returns_trace(client: TestClient) -> None:
    dispatcher = DummyDispatcher()
    app.dependency_overrides[elements_api.get_graph_run_dispatcher_dependency] = lambda: dispatcher
    try:
        create_resp = client.post("/api/elements/graphs", json=_graph_payload())
        graph_id = create_resp.json()["id"]

        run_resp = client.post(
            f"/api/elements/graphs/{graph_id}:execute",
            json={"overrides": {"node_prompt": {"props": {"text": "Elements"}}}},
        )
        assert run_resp.status_code == 202
        run_payload = run_resp.json()
        assert run_payload["status"] == "queued"
        assert run_payload["outputs"] == {}
        assert run_payload["trace"] == []
        assert dispatcher.calls, "Dispatcher should be invoked"

        run_id = run_payload["id"]
        detail_resp = client.get(f"/api/elements/runs/{run_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "queued"
        assert detail_resp.json()["id"] == run_id
    finally:
        app.dependency_overrides.pop(elements_api.get_graph_run_dispatcher_dependency, None)


def test_graph_flow_with_cosmos_repository_override(client: TestClient) -> None:
    repo = InMemoryElementRepository()
    dispatcher = DummyDispatcher()
    app.dependency_overrides[elements_api.get_graph_repository_dependency] = lambda: repo
    app.dependency_overrides[elements_api.get_graph_run_dispatcher_dependency] = lambda: dispatcher
    try:
        create_resp = client.post("/api/elements/graphs", json=_graph_payload())
        assert create_resp.status_code == 201
        assert repo.create_calls == 1
        graph_id = create_resp.json()["id"]

        list_resp = client.get("/api/elements/graphs", params={"tenantId": "lab"})
        assert list_resp.status_code == 200
        assert any(graph["id"] == graph_id for graph in list_resp.json())

        update_payload = _graph_payload()
        update_payload["name"] = "Cosmos"
        update_resp = client.put(f"/api/elements/graphs/{graph_id}", json=update_payload)
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Cosmos"

        run_resp = client.post(
            f"/api/elements/graphs/{graph_id}:execute",
            json={"overrides": {"node_prompt": {"props": {"text": "Cosmos"}}}},
        )
        assert run_resp.status_code == 202
        run_payload = run_resp.json()
        assert run_payload["status"] == "queued"
        assert repo.create_run_calls == 1
        assert dispatcher.calls, "Dispatcher should be triggered"

        run_id = run_payload["id"]
        detail_resp = client.get(f"/api/elements/runs/{run_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "queued"
        assert detail_resp.json()["id"] == run_id

        delete_resp = client.delete(f"/api/elements/graphs/{graph_id}")
        assert delete_resp.status_code == 204
    finally:
        app.dependency_overrides.pop(elements_api.get_graph_repository_dependency, None)
        app.dependency_overrides.pop(elements_api.get_graph_run_dispatcher_dependency, None)


def test_execute_graph_guardrail_blocks_when_limit_reached(client: TestClient) -> None:
    repo = InMemoryElementRepository()
    dispatcher = DummyDispatcher()
    custom_settings = get_settings().model_copy(update={"elements_max_active_runs": 1})

    app.dependency_overrides[elements_api.get_graph_repository_dependency] = lambda: repo
    app.dependency_overrides[elements_api.get_graph_run_dispatcher_dependency] = lambda: dispatcher
    app.dependency_overrides[elements_api.get_settings_dependency] = lambda: custom_settings

    try:
        create_resp = client.post("/api/elements/graphs", json=_graph_payload())
        assert create_resp.status_code == 201
        graph_id = create_resp.json()["id"]

        graph = repo.get_graph(graph_id)
        assert graph is not None
        repo.create_run(graph, status="queued")

        run_resp = client.post(f"/api/elements/graphs/{graph_id}:execute")
        assert run_resp.status_code == 429
        assert "Too many runs" in run_resp.json()["detail"]
        assert not dispatcher.calls
    finally:
        app.dependency_overrides.pop(elements_api.get_graph_repository_dependency, None)
        app.dependency_overrides.pop(elements_api.get_graph_run_dispatcher_dependency, None)
        app.dependency_overrides.pop(elements_api.get_settings_dependency, None)