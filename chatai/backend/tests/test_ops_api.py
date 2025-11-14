from __future__ import annotations

"""Tests for ops status/command endpoints ensuring orchestrator is invoked."""

# @tag:backend,tests,ops

from fastapi.testclient import TestClient


def test_ops_status_uses_snapshot(client: TestClient, ops_stub) -> None:
    response = client.get("/api/ops/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["services"][0]["name"] == "backend"
    assert ops_stub.snapshot_calls == 1


def test_ops_command_dispatches(client: TestClient, ops_stub) -> None:
    response = client.post(
        "/api/ops/command",
        json={"action": "status", "target": "backend", "runtime": "windows"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "status"
    assert ops_stub.dispatch_calls == 1
    assert ops_stub.last_dispatch_kwargs == {
        "action": "status",
        "target": "backend",
        "runtime": "windows",
        "log_lines": 60,
    }
