from __future__ import annotations

"""Storage abstraction supporting SQLite, Cosmos DB, and JSON snapshots."""
# @tag: backend,services,data

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Artifact, Interaction, TailLogEntry
from ..schemas import ArtifactCreate, TailLogEntryCreate
from ..database import get_optional_db_session, get_sessionmaker

try:  # pragma: no cover - optional dependency
    from azure.cosmos import CosmosClient, PartitionKey
    from azure.cosmos.exceptions import CosmosResourceNotFoundError
    from azure.identity import DefaultAzureCredential
except ImportError:  # pragma: no cover
    CosmosClient = None  # type: ignore
    PartitionKey = None  # type: ignore
    CosmosResourceNotFoundError = Exception  # type: ignore
    DefaultAzureCredential = None  # type: ignore


@dataclass
class InteractionRecord:
    id: str
    user_prompt_text: str
    typing_metadata_json: dict[str, Any]
    ai_response_text: str
    model_name: str
    latency_ms: int
    created_at: datetime


@dataclass
class ArtifactRecord:
    id: str
    title: str
    body: str
    owner: str
    category: str
    accent: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class TailLogRecord:
    id: str
    message: str
    source: str
    created_at: datetime


class BaseDataStore(Protocol):
    """Contract for persisting Playground telemetry + artifacts."""

    def record_interaction(
        self,
        *,
        prompt: str,
        metadata: dict[str, Any],
        llm_text: str,
        model_name: str,
        latency_ms: int,
    ) -> InteractionRecord:
        ...

    def list_interactions(self, limit: int) -> list[InteractionRecord]:
        ...

    def count_interactions(self) -> int:
        ...

    def list_artifacts(self, limit: int) -> list[ArtifactRecord]:
        ...

    def create_artifact(self, payload: ArtifactCreate) -> ArtifactRecord:
        ...

    def list_tail_log(self, limit: int) -> list[TailLogRecord]:
        ...

    def create_tail_log_entry(self, payload: TailLogEntryCreate) -> TailLogRecord:
        ...


# --- SQLite implementation ----------------------------------------------------
class SqliteDataStore(BaseDataStore):
    """SQLAlchemy-backed store used for local dev and CI."""

    def __init__(self, session: Session):
        self._session = session

    def record_interaction(
        self,
        *,
        prompt: str,
        metadata: dict[str, Any],
        llm_text: str,
        model_name: str,
        latency_ms: int,
    ) -> InteractionRecord:
        interaction = Interaction(
            id=str(uuid4()),
            user_prompt_text=prompt,
            typing_metadata_json=metadata,
            ai_response_text=llm_text,
            model_name=model_name,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(interaction)
        self._session.commit()
        self._session.refresh(interaction)
        return InteractionRecord(
            id=interaction.id,
            user_prompt_text=interaction.user_prompt_text,
            typing_metadata_json=dict(interaction.typing_metadata_json),
            ai_response_text=interaction.ai_response_text,
            model_name=interaction.model_name,
            latency_ms=interaction.latency_ms,
            created_at=interaction.created_at,
        )

    def list_interactions(self, limit: int) -> list[InteractionRecord]:
        rows = (
            self._session.query(Interaction)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            InteractionRecord(
                id=row.id,
                user_prompt_text=row.user_prompt_text,
                typing_metadata_json=dict(row.typing_metadata_json),
                ai_response_text=row.ai_response_text,
                model_name=row.model_name,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def count_interactions(self) -> int:
        return int(self._session.query(func.count(Interaction.id)).scalar() or 0)

    def list_artifacts(self, limit: int) -> list[ArtifactRecord]:
        rows = (
            self._session.query(Artifact)
            .order_by(Artifact.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            ArtifactRecord(
                id=row.id,
                title=row.title,
                body=row.body,
                owner=row.owner,
                category=row.category,
                accent=row.accent,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def create_artifact(self, payload: ArtifactCreate) -> ArtifactRecord:
        artifact = Artifact(
            id=str(uuid4()),
            title=payload.title,
            body=payload.body,
            owner=payload.owner,
            category=payload.category,
            accent=payload.accent,
        )
        self._session.add(artifact)
        self._session.commit()
        self._session.refresh(artifact)
        return ArtifactRecord(
            id=artifact.id,
            title=artifact.title,
            body=artifact.body,
            owner=artifact.owner,
            category=artifact.category,
            accent=artifact.accent,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    def list_tail_log(self, limit: int) -> list[TailLogRecord]:
        rows = (
            self._session.query(TailLogEntry)
            .order_by(TailLogEntry.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            TailLogRecord(
                id=row.id,
                message=row.message,
                source=row.source,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_tail_log_entry(self, payload: TailLogEntryCreate) -> TailLogRecord:
        entry = TailLogEntry(
            id=str(uuid4()),
            message=payload.message,
            source=payload.source,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return TailLogRecord(
            id=entry.id,
            message=entry.message,
            source=entry.source,
            created_at=entry.created_at,
        )


# --- JSON snapshot implementation --------------------------------------------
class JsonDataStore(BaseDataStore):
    """Lightweight file-backed store for ephemeral or local experiments."""

    def __init__(self, store_path: Path):
        self._path = store_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"interactions": [], "artifacts": [], "tail_log": []})

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self._path)

    def record_interaction(
        self,
        *,
        prompt: str,
        metadata: dict[str, Any],
        llm_text: str,
        model_name: str,
        latency_ms: int,
    ) -> InteractionRecord:
        snapshot = self._read()
        created_at = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "user_prompt_text": prompt,
            "typing_metadata_json": metadata,
            "ai_response_text": llm_text,
            "model_name": model_name,
            "latency_ms": latency_ms,
            "created_at": created_at.isoformat(),
        }
        snapshot["interactions"].insert(0, doc)
        self._write(snapshot)
        return InteractionRecord(
            id=doc["id"],
            user_prompt_text=prompt,
            typing_metadata_json=metadata,
            ai_response_text=llm_text,
            model_name=model_name,
            latency_ms=latency_ms,
            created_at=created_at,
        )

    def list_interactions(self, limit: int) -> list[InteractionRecord]:
        snapshot = self._read()
        records = snapshot.get("interactions", [])[:limit]
        return [
            InteractionRecord(
                id=item["id"],
                user_prompt_text=item["user_prompt_text"],
                typing_metadata_json=item.get("typing_metadata_json", {}),
                ai_response_text=item["ai_response_text"],
                model_name=item["model_name"],
                latency_ms=item.get("latency_ms", 0),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in records
        ]

    def count_interactions(self) -> int:
        snapshot = self._read()
        return len(snapshot.get("interactions", []))

    def list_artifacts(self, limit: int) -> list[ArtifactRecord]:
        snapshot = self._read()
        records = snapshot.get("artifacts", [])[:limit]
        return [
            ArtifactRecord(
                id=item["id"],
                title=item["title"],
                body=item["body"],
                owner=item["owner"],
                category=item["category"],
                accent=item.get("accent"),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )
            for item in records
        ]

    def create_artifact(self, payload: ArtifactCreate) -> ArtifactRecord:
        snapshot = self._read()
        now = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "title": payload.title,
            "body": payload.body,
            "owner": payload.owner,
            "category": payload.category,
            "accent": payload.accent,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        snapshot.setdefault("artifacts", []).insert(0, doc)
        self._write(snapshot)
        return ArtifactRecord(
            id=doc["id"],
            title=doc["title"],
            body=doc["body"],
            owner=doc["owner"],
            category=doc["category"],
            accent=doc["accent"],
            created_at=now,
            updated_at=now,
        )

    def list_tail_log(self, limit: int) -> list[TailLogRecord]:
        snapshot = self._read()
        records = snapshot.get("tail_log", [])[:limit]
        return [
            TailLogRecord(
                id=item["id"],
                message=item["message"],
                source=item["source"],
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in records
        ]

    def create_tail_log_entry(self, payload: TailLogEntryCreate) -> TailLogRecord:
        snapshot = self._read()
        created_at = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "message": payload.message,
            "source": payload.source,
            "created_at": created_at.isoformat(),
        }
        snapshot.setdefault("tail_log", []).insert(0, doc)
        self._write(snapshot)
        return TailLogRecord(
            id=doc["id"],
            message=payload.message,
            source=payload.source,
            created_at=created_at,
        )


# --- Cosmos DB implementation -------------------------------------------------
class CosmosDataStore(BaseDataStore):
    """Azure Cosmos-backed store for multi-region deployments."""

    def __init__(self):
        settings = get_settings()
        if not settings.cosmos_enabled:
            raise RuntimeError("Cosmos DB is not configured but selected as provider")
        if CosmosClient is None:
            raise RuntimeError("azure-cosmos is required for the Cosmos data store")

        self._settings = settings
        credential = None
        if settings.cosmos_prefer_managed_identity and not settings.cosmos_key:
            if DefaultAzureCredential is None:
                raise RuntimeError("azure-identity is required for managed identity auth")
            credential = DefaultAzureCredential()
        else:
            credential = settings.cosmos_key

        self._client = CosmosClient(  # type: ignore[arg-type]
            settings.cosmos_endpoint,
            credential=credential,
            consistency_level=settings.cosmos_consistency,
        )
        self._database = self._client.get_database_client(settings.cosmos_database)
        self._interactions = self._ensure_container(settings.cosmos_interaction_container)
        self._artifacts = self._ensure_container(settings.cosmos_artifact_container)
        self._tail_log = self._ensure_container(settings.cosmos_tail_log_container)

    def _ensure_container(self, name: str):
        if PartitionKey is None:  # pragma: no cover - defensive
            raise RuntimeError("azure-cosmos PartitionKey helper missing")
        try:
            return self._database.create_container_if_not_exists(
                id=name,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400,
            )
        except Exception:  # container exists
            return self._database.get_container_client(name)

    def record_interaction(
        self,
        *,
        prompt: str,
        metadata: dict[str, Any],
        llm_text: str,
        model_name: str,
        latency_ms: int,
    ) -> InteractionRecord:
        created_at = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "user_prompt_text": prompt,
            "typing_metadata_json": metadata,
            "ai_response_text": llm_text,
            "model_name": model_name,
            "latency_ms": latency_ms,
            "created_at": created_at.isoformat(),
        }
        self._interactions.upsert_item(doc)
        return InteractionRecord(
            id=doc["id"],
            user_prompt_text=prompt,
            typing_metadata_json=metadata,
            ai_response_text=llm_text,
            model_name=model_name,
            latency_ms=latency_ms,
            created_at=created_at,
        )

    def list_interactions(self, limit: int) -> list[InteractionRecord]:
        query = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        rows = list(
            self._interactions.query_items(
                query,
                parameters=[{"name": "@limit", "value": limit}],
                enable_cross_partition_query=True,
            )
        )
        return [self._interaction_from_doc(item) for item in rows]

    def count_interactions(self) -> int:
        query = "SELECT VALUE COUNT(1) FROM c"
        rows = list(
            self._interactions.query_items(
                query,
                enable_cross_partition_query=True,
            )
        )
        return int(rows[0]) if rows else 0

    def list_artifacts(self, limit: int) -> list[ArtifactRecord]:
        query = "SELECT * FROM c ORDER BY c.updated_at DESC OFFSET 0 LIMIT @limit"
        rows = list(
            self._artifacts.query_items(
                query,
                parameters=[{"name": "@limit", "value": limit}],
                enable_cross_partition_query=True,
            )
        )
        return [self._artifact_from_doc(item) for item in rows]

    def create_artifact(self, payload: ArtifactCreate) -> ArtifactRecord:
        now = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "title": payload.title,
            "body": payload.body,
            "owner": payload.owner,
            "category": payload.category,
            "accent": payload.accent,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._artifacts.upsert_item(doc)
        return self._artifact_from_doc(doc)

    def list_tail_log(self, limit: int) -> list[TailLogRecord]:
        query = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        rows = list(
            self._tail_log.query_items(
                query,
                parameters=[{"name": "@limit", "value": limit}],
                enable_cross_partition_query=True,
            )
        )
        return [self._tail_log_from_doc(item) for item in rows]

    def create_tail_log_entry(self, payload: TailLogEntryCreate) -> TailLogRecord:
        now = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid4()),
            "message": payload.message,
            "source": payload.source,
            "created_at": now.isoformat(),
        }
        self._tail_log.upsert_item(doc)
        return self._tail_log_from_doc(doc)

    @staticmethod
    def _artifact_from_doc(doc: dict[str, Any]) -> ArtifactRecord:
        return ArtifactRecord(
            id=doc["id"],
            title=doc["title"],
            body=doc["body"],
            owner=doc["owner"],
            category=doc["category"],
            accent=doc.get("accent"),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

    @staticmethod
    def _tail_log_from_doc(doc: dict[str, Any]) -> TailLogRecord:
        return TailLogRecord(
            id=doc["id"],
            message=doc["message"],
            source=doc["source"],
            created_at=datetime.fromisoformat(doc["created_at"]),
        )

    @staticmethod
    def _interaction_from_doc(doc: dict[str, Any]) -> InteractionRecord:
        return InteractionRecord(
            id=doc["id"],
            user_prompt_text=doc["user_prompt_text"],
            typing_metadata_json=doc.get("typing_metadata_json", {}),
            ai_response_text=doc["ai_response_text"],
            model_name=doc.get("model_name", "unknown"),
            latency_ms=doc.get("latency_ms", 0),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )


# --- Dependency helper --------------------------------------------------------
def get_data_store(
    session: Session | None = Depends(get_optional_db_session),
) -> BaseDataStore:
    settings = get_settings()
    return _build_data_store(settings, session)


def _build_data_store(settings, session: Session | None) -> BaseDataStore:
    provider = settings.database_provider

    if provider == "sqlite":
        if session is None:
            raise RuntimeError("SQLite data store requires a database session")
        return SqliteDataStore(session)

    if provider == "cosmos":
        return CosmosDataStore()

    if provider == "json":
        return JsonDataStore(settings.json_store_path)

    raise RuntimeError(f"Unsupported DATABASE_PROVIDER: {provider}")


@contextmanager
def data_store_context() -> Any:
    """Yield a data store instance outside of FastAPI dependency injection."""

    settings = get_settings()
    session: Session | None = None
    try:
        if settings.database_provider == "sqlite":
            session_factory = get_sessionmaker()
            session = session_factory()
        yield _build_data_store(settings, session)
    finally:
        if session is not None:
            session.close()
