from __future__ import annotations

"""Helper utilities for publishing Playground manifests from the Kitchen."""

from dataclasses import dataclass
import json
import os
from typing import Any

import requests
from requests import Response

DEFAULT_BASE_URL = os.getenv("PLAYGROUND_API_URL", "http://localhost:8000/api")


@dataclass
class ManifestPublishResult:
    tenant: str
    playground: str
    revision: int
    revision_label: str | None
    checksum: str
    created_at: str
    url: str
    manifest: dict[str, Any]


class ManifestPublishError(RuntimeError):
    pass


class ManifestPublisher:
    """Thin wrapper over the backend manifest API.

    Parameters
    ----------
    base_url:
        Base API endpoint (defaults to the PLAYGROUND_API_URL environment variable).
    token:
        Optional bearer token for authenticated deployments.
    timeout:
        HTTP timeout in seconds (default 15s).
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.token = token or os.getenv("PLAYGROUND_API_TOKEN")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    def publish(
        self,
        *,
        tenant: str,
        playground: str,
        manifest: dict[str, Any],
        cookbook: str | None = None,
        recipe: str | None = None,
        author: str | None = None,
        notes: str | None = None,
        revision: int | None = None,
        revision_label: str | None = None,
    ) -> ManifestPublishResult:
        payload = {
            "manifest": manifest,
            "cookbook": cookbook,
            "recipe": recipe,
            "author": author,
            "notes": notes,
            "revision": revision,
            "revision_label": revision_label,
        }
        response = self._request(
            "POST",
            f"/playgrounds/{tenant}/{playground}/manifests",
            json=_compact(payload),
        )
        data = response.json()
        return ManifestPublishResult(
            tenant=data["tenant"],
            playground=data["playground"],
            revision=data["revision"],
            revision_label=data.get("revision_label"),
            checksum=data["checksum"],
            created_at=data["created_at"],
            url=f"{self.base_url}/playgrounds/{tenant}/{playground}/manifests/{data['revision']}",
            manifest=data["manifest"],
        )

    def latest(self, *, tenant: str, playground: str) -> dict[str, Any] | None:
        response = self._request(
            "GET", f"/playgrounds/{tenant}/{playground}/manifests/latest", allow_404=True
        )
        if response.status_code == 404:
            return None
        return response.json()

    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, *, allow_404: bool = False, **kwargs) -> Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json")
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = self._session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise ManifestPublishError(f"Request to {url} failed: {exc}") from exc

        if response.status_code >= 400 and not (allow_404 and response.status_code == 404):
            raise ManifestPublishError(_format_error(response))
        return response


# ----------------------------------------------------------------------
def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _format_error(response: Response) -> str:
    message = f"Manifest API error ({response.status_code})"
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else None
        if detail:
            return f"{message}: {detail}"
        return f"{message}: {json.dumps(body)}"
    except ValueError:
        return f"{message}: {response.text.strip()}"
*** End ***