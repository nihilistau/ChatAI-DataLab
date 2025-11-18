from __future__ import annotations

"""Tests for the persistent commands API surface."""

# @tag:backend,tests,commands

import sys
from pathlib import Path

import pytest

from app.services.command_store import CommandStore, set_command_store


@pytest.fixture()
def command_store_tmp(tmp_path: Path) -> CommandStore:
    store = CommandStore(tmp_path / "commands.json")
    set_command_store(store)
    yield store
    set_command_store(None)


def test_create_and_list_commands(client, command_store_tmp):  # noqa: ANN001
    payload = {
        "label": "List backend jobs",
        "command": "python -m this",
        "tags": ["diagnostic"],
        "description": "Sample command",
    }

    create_resp = client.post("/api/commands", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["label"] == payload["label"]
    assert created["last_status"] == "never-run"

    list_resp = client.get("/api/commands")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["id"] == created["id"]


def test_run_command_records_history(client, command_store_tmp):  # noqa: ANN001
    command = f"{sys.executable} -c \"print('hello-commands')\""
    create_resp = client.post(
        "/api/commands",
        json={"label": "echo", "command": command},
    )
    command_id = create_resp.json()["id"]

    run_resp = client.post(f"/api/commands/{command_id}/run", json={"dry_run": True})
    assert run_resp.status_code == 200
    payload = run_resp.json()
    assert payload["last_status"] == "succeeded"
    assert len(payload["history"]) == 1
    assert payload["history"][0]["notes"] == "dry-run"
    assert payload["history"][0]["failed"] is False
    assert payload["history"][0]["command"] == command


def test_list_commands_supports_filters(client, command_store_tmp):  # noqa: ANN001
    cmd_success = client.post(
        "/api/commands",
        json={"label": "ok", "command": "echo ok", "tags": ["ops"]},
    ).json()
    cmd_failed = client.post(
        "/api/commands",
        json={"label": "bad", "command": "exit 1", "tags": ["ops", "diagnostic"]},
    ).json()
    cmd_other = client.post(
        "/api/commands",
        json={"label": "misc", "command": "echo misc", "tags": ["misc"]},
    ).json()

    command_store_tmp.record_execution(
        cmd_success["id"], status="succeeded", exit_code=0, output="ok", notes="manual"
    )
    command_store_tmp.record_execution(
        cmd_failed["id"], status="failed", exit_code=1, output="boom", notes="manual"
    )
    command_store_tmp.record_execution(
        cmd_other["id"], status="succeeded", exit_code=0, output="misc", notes="manual"
    )

    succeeded_resp = client.get("/api/commands", params={"status": "succeeded"})
    assert succeeded_resp.status_code == 200
    succeeded_ids = [item["id"] for item in succeeded_resp.json()]
    assert cmd_failed["id"] not in succeeded_ids
    assert set(succeeded_ids) == {cmd_success["id"], cmd_other["id"]}

    tag_resp = client.get("/api/commands", params={"tag": "diagnostic"})
    assert tag_resp.status_code == 200
    data = tag_resp.json()
    assert len(data) == 1 and data[0]["id"] == cmd_failed["id"]

    limit_resp = client.get("/api/commands", params={"limit": 2})
    assert limit_resp.status_code == 200
    assert len(limit_resp.json()) == 2


def test_get_command_history_filters_and_limits(client, command_store_tmp):  # noqa: ANN001
    create_resp = client.post(
        "/api/commands",
        json={"label": "history", "command": "echo history"},
    )
    command_id = create_resp.json()["id"]

    command_store_tmp.record_execution(
        command_id,
        status="succeeded",
        exit_code=0,
        output="first",
        notes="ok",
    )
    command_store_tmp.record_execution(
        command_id,
        status="failed",
        exit_code=1,
        output="second",
        notes="bad",
    )

    resp = client.get(f"/api/commands/{command_id}/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    failed_only = client.get(
        f"/api/commands/{command_id}/history", params={"status": "failed", "limit": 1}
    )
    assert failed_only.status_code == 200
    data = failed_only.json()
    assert len(data) == 1
    assert data[0]["status"] == "failed"