from __future__ import annotations

"""REST routes bridging ChatAI, Ops Deck, and the Tail log."""
# @tag:backend,api,ops

# --- Imports -----------------------------------------------------------------
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db_session
from ..models import Artifact, Interaction, TailLogEntry
from ..schemas import (
    ArtifactCreate,
    ArtifactRead,
    ChatPayload,
    ChatResponse,
    OpsCommandRequest,
    OpsCommandResponse,
    OpsStatus,
    SearchTelemetrySummary,
    TailLogEntryCreate,
    TailLogEntryRead,
)
from ..services.llm_client import get_llm_client
from ..services.search_telemetry import get_search_telemetry_summary

from app.services.orchestrator import get_orchestrator  # type: ignore  # noqa: E402


# --- Router setup ------------------------------------------------------------
router = APIRouter(tags=["chat", "canvas"])


@router.post("/chat", response_model=ChatResponse)
async def create_chat_completion(
    payload: ChatPayload,
    session: Session = Depends(get_db_session),
):
    settings = get_settings()
    llm_client = get_llm_client()

    try:
        llm_result = await llm_client.generate(payload.final_prompt_text)
    except Exception as exc:  # pragma: no cover - network errors
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve LLM response",
        ) from exc

    interaction = Interaction(
        id=str(uuid4()),
        user_prompt_text=payload.final_prompt_text,
        typing_metadata_json=payload.to_metadata_dict(),
        ai_response_text=llm_result.text,
        model_name=llm_result.model_name,
        latency_ms=llm_result.latency_ms,
        created_at=datetime.now(timezone.utc),
    )
    session.add(interaction)
    session.commit()

    return ChatResponse(
        interaction_id=interaction.id,
        ai_response_text=interaction.ai_response_text,
        model_name=interaction.model_name or settings.openai_model,
        latency_ms=interaction.latency_ms,
        created_at=interaction.created_at,
    )


@router.get("/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    limit: int = Query(8, ge=1, le=64),
    session: Session = Depends(get_db_session),
):
    return (
        session.query(Artifact)
        .order_by(Artifact.updated_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(
    payload: ArtifactCreate,
    session: Session = Depends(get_db_session),
):
    artifact = Artifact(
        title=payload.title,
        body=payload.body,
        owner=payload.owner,
        accent=payload.accent,
        category=payload.category,
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


@router.get("/tail-log", response_model=list[TailLogEntryRead])
def list_tail_log(
    limit: int = Query(18, ge=1, le=200),
    session: Session = Depends(get_db_session),
):
    return (
        session.query(TailLogEntry)
        .order_by(TailLogEntry.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/tail-log", response_model=TailLogEntryRead, status_code=status.HTTP_201_CREATED)
def create_tail_log_entry(
    payload: TailLogEntryCreate,
    session: Session = Depends(get_db_session),
):
    entry = TailLogEntry(message=payload.message, source=payload.source)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.get("/ops/status", response_model=OpsStatus, tags=["ops"])
def get_ops_status():
    snapshot = get_orchestrator().snapshot()
    return OpsStatus.model_validate(snapshot)


@router.post("/ops/command", response_model=OpsCommandResponse, tags=["ops"])
def control_ops(payload: OpsCommandRequest):
    result = get_orchestrator().dispatch(
        action=payload.action,
        target=payload.target or "all",
        runtime=payload.runtime,
        log_lines=payload.log_lines or 60,
    )
    return OpsCommandResponse(**result)


@router.get("/ops/search-telemetry", response_model=SearchTelemetrySummary, tags=["ops"])
def fetch_search_telemetry_summary():
    summary = get_search_telemetry_summary()
    return SearchTelemetrySummary(**summary)
