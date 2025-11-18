from __future__ import annotations

"""REST routes bridging the Playground stack, Ops Deck, and the Tail log."""
# @tag:backend,api,ops

# --- Imports -----------------------------------------------------------------
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import get_settings
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
from ..services.data_store import BaseDataStore, get_data_store
from ..services.llm_client import get_llm_client
from ..services.search_telemetry import get_search_telemetry_summary

from app.services.orchestrator import get_orchestrator  # type: ignore  # noqa: E402


# --- Router setup ------------------------------------------------------------
router = APIRouter(tags=["chat", "canvas"])


@router.post("/chat", response_model=ChatResponse)
async def create_chat_completion(
    payload: ChatPayload,
    data_store: BaseDataStore = Depends(get_data_store),
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

    interaction = data_store.record_interaction(
        prompt=payload.final_prompt_text,
        metadata=payload.to_metadata_dict(),
        llm_text=llm_result.text,
        model_name=llm_result.model_name,
        latency_ms=llm_result.latency_ms,
    )

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
    data_store: BaseDataStore = Depends(get_data_store),
):
    records = data_store.list_artifacts(limit)
    return [ArtifactRead.model_validate(asdict(record)) for record in records]


@router.post("/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_artifact(
    payload: ArtifactCreate,
    data_store: BaseDataStore = Depends(get_data_store),
):
    record = data_store.create_artifact(payload)
    return ArtifactRead.model_validate(asdict(record))


@router.get("/tail-log", response_model=list[TailLogEntryRead])
def list_tail_log(
    limit: int = Query(18, ge=1, le=200),
    data_store: BaseDataStore = Depends(get_data_store),
):
    entries = data_store.list_tail_log(limit)
    return [TailLogEntryRead.model_validate(asdict(entry)) for entry in entries]


@router.post("/tail-log", response_model=TailLogEntryRead, status_code=status.HTTP_201_CREATED)
def create_tail_log_entry(
    payload: TailLogEntryCreate,
    data_store: BaseDataStore = Depends(get_data_store),
):
    record = data_store.create_tail_log_entry(payload)
    return TailLogEntryRead.model_validate(asdict(record))


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
