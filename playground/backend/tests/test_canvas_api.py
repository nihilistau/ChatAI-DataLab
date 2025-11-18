from __future__ import annotations

"""CRUD smoke tests for canvas + tail-log HTTP endpoints."""
# @tag:backend,tests,api

from fastapi.testclient import TestClient


def test_artifact_crud_flow(client: TestClient):
    """Exercise list/create flows to ensure artifact endpoints are wired."""

    list_response = client.get("/api/artifacts")
    assert list_response.status_code == 200
    assert list_response.json() == []

    payload = {
        "title": "Latency digest",
        "body": "Rolling latency histogram exported from the last 25 prompts.",
        "owner": "assistant",
        "category": "artifact",
        "accent": "violet",
    }
    create_response = client.post("/api/artifacts", json=payload)
    assert create_response.status_code == 201
    artifact = create_response.json()
    assert artifact["title"] == payload["title"]

    list_response = client.get("/api/artifacts")
    artifacts = list_response.json()
    assert len(artifacts) == 1
    assert artifacts[0]["id"] == artifact["id"]


def test_tail_log_flow(client: TestClient):
    """Validate append + retrieval ordering for the tail log API."""

    initial = client.get("/api/tail-log")
    assert initial.status_code == 200
    assert initial.json() == []

    entry_payload = {"message": "boot · canvas online", "source": "system"}
    create_response = client.post("/api/tail-log", json=entry_payload)
    assert create_response.status_code == 201
    entry = create_response.json()
    assert entry["message"].startswith("boot")

    second_payload = {"message": "deck · added hypothesis", "source": "deck"}
    client.post("/api/tail-log", json=second_payload)

    history = client.get("/api/tail-log")
    history_data = history.json()
    assert len(history_data) == 2
    assert history_data[0]["message"].startswith("deck")
    assert history_data[1]["message"].startswith("boot")
