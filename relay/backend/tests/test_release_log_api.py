from __future__ import annotations

"""Coverage for the release log API surface."""
# @tag: backend,tests,release-log

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


def _write_release_log(entries: list[dict]) -> Path:
    path = Path(os.environ["RELEASE_LOG_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry))
            handle.write("\n")
    return path


def test_release_log_empty(client: TestClient) -> None:
    response = client.get("/api/release-log?limit=5")
    assert response.status_code == 200
    assert response.json() == []


def test_release_log_entries_returned_with_newest_first(client: TestClient) -> None:
    older = {
        "timestamp": "2024-11-20T05:00:00+00:00",
        "tag": "v1",
        "branch": "main",
        "commit": "abc123",
        "checkpoint_id": "101",
        "release_dir": "release_artifacts/v1",
        "timeline": [
            {
                "name": "checkpoint",
                "status": "ok",
                "started_at": "2024-11-20T05:00:01+00:00",
                "ended_at": "2024-11-20T05:00:02+00:00",
            }
        ],
        "notes": "pipeline entry",
    }
    newer = {
        "timestamp": "2024-11-21T05:00:00+00:00",
        "kind": "workflow_harness",
        "release_mode": "dry-run",
        "goal_milestone": "Ops workflow harness",
        "timeline": [],
        "options": {"release_mode": "dry-run"},
    }
    _write_release_log([older, newer])

    response = client.get("/api/release-log?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert [entry["kind"] for entry in payload] == ["workflow_harness", "release_pipeline"]
    assert payload[0]["timeline"] == []
    assert payload[1]["tag"] == "v1"
    assert all("id" in entry for entry in payload)
