from __future__ import annotations

from fastapi.testclient import TestClient


def _publish(client: TestClient, revision: int | None = None, *, author: str = "builder"):
    payload = {
        "manifest": {"layout": {"sections": []}},
        "author": author,
        "notes": "test",
    }
    if revision is not None:
        payload["revision"] = revision
    response = client.post("/api/playgrounds/acme/demo/manifests", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_manifest_publish_auto_revision(client: TestClient) -> None:
    first = _publish(client)
    assert first["revision"] == 1

    second = _publish(client)
    assert second["revision"] == 2


def test_manifest_publish_with_revision_hint(client: TestClient) -> None:
    _publish(client, revision=3)
    listed = client.get("/api/playgrounds/acme/demo/manifests").json()
    assert listed[0]["revision"] == 3


def test_manifest_latest_endpoint(client: TestClient) -> None:
    _publish(client)
    latest = client.get("/api/playgrounds/acme/demo/manifests/latest")
    assert latest.status_code == 200
    assert latest.json()["revision"] == 1


def test_manifest_specific_revision_lookup(client: TestClient) -> None:
    _publish(client)
    response = client.get("/api/playgrounds/acme/demo/manifests/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["revision"] == 1


def test_manifest_revision_conflict(client: TestClient) -> None:
    first = _publish(client)
    assert first["revision"] == 1

    conflict = client.post(
        "/api/playgrounds/acme/demo/manifests",
        json={
            "manifest": {"layout": {"sections": []}},
            "author": "builder",
            "revision": 1,
        },
    )
    assert conflict.status_code == 409
