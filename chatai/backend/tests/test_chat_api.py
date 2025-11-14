"""Integration tests for the chat completion API route."""

# @tag: backend,tests,api

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import get_engine
from app.models import Interaction
from app.schemas import ChatPayload


def test_chat_endpoint_persists_payload(client: TestClient):
    """Ensure the POST /api/chat endpoint saves user payloads and returns stubbed response."""
    payload: ChatPayload = ChatPayload(
        final_prompt_text="Explain typed pauses",
        total_duration_ms=1200,
        token_estimate=42,
        keystroke_events=[{"key": "a", "code": "KeyA", "timestamp_ms": 1}],
        pause_events=[{"start_timestamp_ms": 1, "duration_ms": 700}],
        edit_history=[{"timestamp_ms": 1, "text": "Explain"}],
        session_id="test-session",
        ui_version="web-test",
    )

    response = client.post("/api/chat", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["ai_response_text"].startswith("stubbed::")
    assert data["model_name"] == "stub-model"

    engine = get_engine()
    with sessionmaker(bind=engine)() as session:
        rows = session.query(Interaction).all()
        assert len(rows) == 1
        interaction = rows[0]
        assert interaction.user_prompt_text == payload.final_prompt_text
        assert interaction.typing_metadata_json["keystroke_events"]


def test_chat_endpoint_requires_prompt_text(client: TestClient):
    """Validate that a request without prompt text is rejected by FastAPI validation."""
    payload = {
        "final_prompt_text": "",
        "total_duration_ms": 0,
        "keystroke_events": [],
        "pause_events": [],
        "edit_history": [],
    }

    response = client.post("/api/chat", json=payload)

    assert response.status_code == 422
