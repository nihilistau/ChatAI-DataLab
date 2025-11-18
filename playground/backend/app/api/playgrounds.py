from __future__ import annotations

"""API surface for publishing Playground manifests from the Kitchen."""

# @tag:backend,api,playgrounds

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..database import get_db_session
from ..models import PlaygroundManifest
from ..schemas import PlaygroundManifestCreate, PlaygroundManifestRead

router = APIRouter(prefix="/playgrounds", tags=["playgrounds"])


def _serialize_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"))


def _checksum(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(_serialize_manifest(manifest).encode("utf-8")).hexdigest()


def _latest_revision(session: Session, tenant: str, playground: str) -> int | None:
    record = (
        session.query(PlaygroundManifest.revision)
        .filter(PlaygroundManifest.tenant == tenant, PlaygroundManifest.playground == playground)
        .order_by(PlaygroundManifest.revision.desc())
        .first()
    )
    return record[0] if record else None


def _manifest_query(session: Session, tenant: str, playground: str):
    return session.query(PlaygroundManifest).filter(
        PlaygroundManifest.tenant == tenant,
        PlaygroundManifest.playground == playground,
    )


@router.post(
    "/{tenant}/{playground}/manifests",
    response_model=PlaygroundManifestRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_manifest(
    payload: PlaygroundManifestCreate,
    tenant: str = Path(..., min_length=2, max_length=120),
    playground: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    latest_revision = _latest_revision(session, tenant, playground)
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

    manifest = PlaygroundManifest(
        tenant=tenant,
        playground=playground,
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
    return PlaygroundManifestRead.model_validate(manifest)


@router.get("/{tenant}/{playground}/manifests", response_model=list[PlaygroundManifestRead])
def list_manifests(
    tenant: str = Path(..., min_length=2, max_length=120),
    playground: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifests = (
        _manifest_query(session, tenant, playground)
        .order_by(PlaygroundManifest.revision.desc())
        .all()
    )
    return [PlaygroundManifestRead.model_validate(item) for item in manifests]


@router.get(
    "/{tenant}/{playground}/manifests/latest",
    response_model=PlaygroundManifestRead,
)
def get_latest_manifest(
    tenant: str = Path(..., min_length=2, max_length=120),
    playground: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifest = (
        _manifest_query(session, tenant, playground)
        .order_by(PlaygroundManifest.revision.desc())
        .first()
    )
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No manifest for namespace")
    return PlaygroundManifestRead.model_validate(manifest)


@router.get(
    "/{tenant}/{playground}/manifests/{revision}",
    response_model=PlaygroundManifestRead,
)
def get_manifest_by_revision(
    revision: int,
    tenant: str = Path(..., min_length=2, max_length=120),
    playground: str = Path(..., min_length=2, max_length=120),
    session: Session = Depends(get_db_session),
):
    manifest = (
        _manifest_query(session, tenant, playground)
        .filter(PlaygroundManifest.revision == revision)
        .first()
    )
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest revision not found")
    return PlaygroundManifestRead.model_validate(manifest)
