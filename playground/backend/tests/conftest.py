from __future__ import annotations

"""Pytest fixtures and LLM stubs for backend integration tests."""
# @tag:backend,tests

# --- Imports -----------------------------------------------------------------
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

# Ensure both backend (this package) and repository root are discoverable so
# imports like ``controlplane`` resolve during test runs launched from
# ``playground/backend``.
BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
for entry in (str(BASE_DIR), str(REPO_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from app.config import get_settings
from app.database import Base, get_db_session, get_engine, reset_db_state
from app.services import llm_client
from app.services import orchestrator as orchestrator_service
from app.services.notebook_runner import NotebookJob, set_notebook_runner
from main import app


class StubOrchestrator:
    """Captures Ops Deck API invocations during tests."""

    def __init__(self) -> None:
        self.snapshot_calls = 0
        self.dispatch_calls = 0
        self.last_dispatch_kwargs: dict | None = None

    def snapshot(self, include_logs: bool | None = None) -> dict:
        self.snapshot_calls += 1
        return {
            "services": [
                {
                    "name": "backend",
                    "state": "running",
                    "runtime": "windows",
                    "display_name": "Playground FastAPI",
                    "command": "uvicorn main:app",
                }
            ],
            "processes": [],
            "network": {
                "hostname": "lab-n1",
                "platform": "windows",
                "uptime": 123,
                "bytes_sent": 0,
                "bytes_recv": 0,
                "interfaces": {},
            },
            "logs": {"backend": ["boot"]},
            "timestamp": 100.0,
        }

    def dispatch(self, **kwargs) -> dict:
        self.dispatch_calls += 1
        self.last_dispatch_kwargs = kwargs
        return {
            "action": kwargs.get("action", "status"),
            "target": kwargs.get("target", "all"),
            "runtime": kwargs.get("runtime", "auto"),
            "output": "ok",
            "timestamp": 101.0,
        }


class StubLLM:
    """Minimal async-compatible stand-in for the production LLM client."""

    async def generate(self, prompt: str) -> llm_client.LLMResult:
        return llm_client.LLMResult(
            text=f"stubbed::{prompt}",
            model_name="stub-model",
            latency_ms=42,
        )


class StubNotebookRunner:
    def __init__(self) -> None:
        self.jobs = [
            NotebookJob(
                id="job-1",
                name="control_center_playground.ipynb",
                status="succeeded",
                output_path="/tmp/job-1.ipynb",
                parameters={"DB_PATH": "sqlite:///example.db"},
            )
        ]
        self.submit_calls: list[tuple[str, dict]] = []

    def list_jobs(self):
        return list(self.jobs)

    async def submit(self, name: str, parameters: dict | None = None):
        payload = parameters or {}
        job = NotebookJob(id=f"job-{len(self.jobs) + 1}", name=name, parameters=payload, status="succeeded")
        self.jobs.insert(0, job)
        self.submit_calls.append((name, payload))
        return job


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    """Yield a fully isolated TestClient with temp DB + stubbed LLM layer."""

    os.environ["DATABASE_PATH"] = str(tmp_path / "interactions.db")
    os.environ["ENVIRONMENT"] = "local"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    reset_db_state()
    llm_client.reset_llm_client()

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    test_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_db() -> Generator[Session, None, None]:
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db
    llm_client._llm_client = StubLLM()  # type: ignore[attr-defined]

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_db_state()
    llm_client.reset_llm_client()


@pytest.fixture()
def ops_stub() -> Generator[StubOrchestrator, None, None]:
    """Swap the global orchestrator with a deterministic stub during tests."""

    stub = StubOrchestrator()
    original = orchestrator_service.get_orchestrator()
    orchestrator_service.set_orchestrator(stub)
    try:
        yield stub
    finally:
        orchestrator_service.set_orchestrator(original)


@pytest.fixture()
def notebook_runner_stub() -> Generator[StubNotebookRunner, None, None]:
    stub = StubNotebookRunner()
    set_notebook_runner(stub)
    try:
        yield stub
    finally:
        set_notebook_runner(None)
