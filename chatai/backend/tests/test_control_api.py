from __future__ import annotations

"""Tests for the Control Center API surface powering the Playground."""

# @tag:backend,tests,control

from fastapi.testclient import TestClient


def test_control_status_uses_orchestrator(client: TestClient, ops_stub) -> None:
    response = client.get("/api/control/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["services"][0]["name"] == "backend"
    assert payload["logs"] == {}
    assert ops_stub.snapshot_calls == 1


def test_control_logs_returns_tail(client: TestClient, ops_stub) -> None:
    response = client.get("/api/control/logs", params={"service": "backend", "lines": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "backend"
    assert payload["lines"] == ["boot"]
    assert ops_stub.snapshot_calls >= 1


def test_control_widgets_payload(client: TestClient) -> None:
    response = client.get("/api/control/widgets")
    assert response.status_code == 200
    payload = response.json()
    assert "metrics" in payload and len(payload["metrics"]) == 3
    assert payload["ru_budget"]["total"] > payload["ru_budget"]["consumed"]


def test_list_notebook_jobs(client: TestClient, notebook_runner_stub) -> None:
    response = client.get("/api/control/notebooks")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 1
    assert jobs[0]["name"].endswith(".ipynb")


def test_trigger_notebook_job(client: TestClient, notebook_runner_stub) -> None:
    response = client.post(
        "/api/control/notebooks",
        json={"name": "control_center_playground.ipynb", "parameters": {"DB_PATH": "sqlite:///tmp.db"}},
    )
    assert response.status_code == 202
    assert notebook_runner_stub.submit_calls[0][0] == "control_center_playground.ipynb"