from __future__ import annotations

"""Tests for the Elements graph CRUD + execution endpoints."""

# @tag:backend,tests,elements

from fastapi.testclient import TestClient


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
    create_resp = client.post("/api/elements/graphs", json=_graph_payload())
    graph_id = create_resp.json()["id"]

    run_resp = client.post(
        f"/api/elements/graphs/{graph_id}:execute",
        json={"overrides": {"node_prompt": {"props": {"text": "Elements"}}}},
    )
    assert run_resp.status_code == 202
    run_payload = run_resp.json()
    assert run_payload["status"] == "succeeded"
    assert run_payload["outputs"].get("status") == "queued"
    assert len(run_payload["trace"]) == 3

    run_id = run_payload["id"]
    detail_resp = client.get(f"/api/elements/runs/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == run_id