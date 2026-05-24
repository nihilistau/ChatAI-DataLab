from __future__ import annotations

"""API surface for publishing Relay manifests from the Workshop."""

# @tag:backend,api,relays

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..database import get_db_session
from ..models import RelayManifest
from ..schemas import RelayManifestCreate, RelayManifestRead

router = APIRouter(prefix="/relays", tags=["relays"])


def _serialize_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"))


def _checksum(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(_serialize_manifest(manifest).encode("utf-8")).hexdigest()


def _latest_revision(session: Session, tenant: str, relay: str) -> int | None:
    record = (
        session.query(RelayManifest.revision)
        .filter(RelayManifest.tenant == tenant, RelayManifest.relay == relay)
        .order_by(RelayManifest.revision.desc())
        .first()
    )
    return record[0] if record else None


def _manifest_query(session: Session, tenant: str, relay: str):
    return session.query(RelayManifest).filter(
        RelayManifest.tenant == tenant,
        RelayManifest.relay == relay,
    )


@router.post(
    "/{tenant}/{relay}/manifests",
    response_model=RelayManifestRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_manifest(
    payload: RelayManifestCreate,
    tenant: str = Path(..., min_length=2, max_length=120),
    relay: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    latest_revision = _latest_revision(session, tenant, relay)
    next_revision = (latest_revision or 0) + 1
    revision = payload.revision if payload.revision is not None else next_revision

    if (
        payload.revision is not None
        and latest_revision is not None
        and payload.revision <= latest_revision
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Revision conflict: requested revision "
                f"{payload.revision} is not newer than existing revision {latest_revision}."
            ),
        )

    manifest = RelayManifest(
        tenant=tenant,
        relay=relay,
        revision=revision,
        revision_label=payload.revision_label,
        manifest=payload.manifest,
        cookbook=payload.cookbook,
        recipe=payload.recipe,
        author=payload.author,
        notes=payload.notes,
        checksum=_checksum(payload.manifest),
    )
    session.add(manifest)
    session.commit()
    session.refresh(manifest)
    return RelayManifestRead.model_validate(manifest)


@router.get("/{tenant}/{relay}/manifests", response_model=list[RelayManifestRead])
def list_manifests(
    tenant: str = Path(..., min_length=2, max_length=120),
    relay: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifests = (
        _manifest_query(session, tenant, relay)
        .order_by(RelayManifest.revision.desc())
        .all()
    )
    return [RelayManifestRead.model_validate(item) for item in manifests]


@router.get(
    "/{tenant}/{relay}/manifests/latest",
    response_model=RelayManifestRead,
)
def get_latest_manifest(
    tenant: str = Path(..., min_length=2, max_length=120),
    relay: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifest = (
        _manifest_query(session, tenant, relay)
        .order_by(RelayManifest.revision.desc())
        .first()
    )
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No manifest for namespace")
    return RelayManifestRead.model_validate(manifest)


@router.get(
    "/{tenant}/{relay}/manifests/{revision}",
    response_model=RelayManifestRead,
)
def get_manifest_by_revision(
    revision: int,
    tenant: str = Path(..., min_length=2, max_length=120),
    relay: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifest = (
        _manifest_query(session, tenant, relay)
        .filter(RelayManifest.revision == revision)
        .first()
    )
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest revision not found")
    return RelayManifestRead.model_validate(manifest)
