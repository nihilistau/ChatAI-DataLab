"""Reusable helpers for turning typing metadata JSON into analytic features."""
# @tag: kitchen,scripts,analytics

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from kitchen.lab_paths import data_path
from playground.backend.app.services.data_store import data_store_context

DEFAULT_COLUMN_ORDER = [
    "id",
    "user_prompt_text",
    "typing_metadata_json",
    "ai_response_text",
    "model_name",
    "latency_ms",
    "created_at",
]
FALLBACK_DATASTORE_LIMIT = 250


def load_interactions(
    db_path: str | os.PathLike[str] | None = None,
    *,
    limit: int | None = None,
) -> pd.DataFrame:
    """Return a DataFrame of chat interactions from the configured data store.

    When ``db_path`` is provided the helper falls back to SQLite for backwards
    compatibility (primarily for tests and ad-hoc notebook probes). Otherwise it
    uses :func:`data_store_context` so Kitchen/DataLab assets honor whichever
    provider the Playground backend is currently using (SQLite, Cosmos, JSON).
    """

    if db_path is not None:
        return _load_interactions_from_sqlite(Path(db_path))
    return _load_interactions_from_data_store(limit=limit)


def _load_interactions_from_sqlite(path: Path) -> pd.DataFrame:
    import sqlite3

    target = Path(path)
    if not target.exists():
        return pd.DataFrame(columns=DEFAULT_COLUMN_ORDER)
    conn = sqlite3.connect(target)
    try:
        return pd.read_sql_query("SELECT * FROM interactions ORDER BY created_at DESC", conn)
    finally:
        conn.close()


def _load_interactions_from_data_store(limit: int | None = None) -> pd.DataFrame:
    with data_store_context() as store:
        target_limit = _resolve_limit(store, limit)
        if target_limit <= 0:
            return pd.DataFrame(columns=DEFAULT_COLUMN_ORDER)
        records = store.list_interactions(limit=target_limit)
    return _records_to_frame(records)


def _resolve_limit(store, limit: int | None) -> int:
    if limit is not None:
        return max(int(limit), 0)
    try:
        count = int(store.count_interactions())
    except Exception:
        return FALLBACK_DATASTORE_LIMIT
    return max(count, 0)


def _records_to_frame(records: Sequence) -> pd.DataFrame:
    rows = [
        {
            "id": record.id,
            "user_prompt_text": record.user_prompt_text,
            "typing_metadata_json": json.dumps(record.typing_metadata_json or {}),
            "ai_response_text": record.ai_response_text,
            "model_name": record.model_name,
            "latency_ms": record.latency_ms,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]
    if not rows:
        return pd.DataFrame(columns=DEFAULT_COLUMN_ORDER)
    return pd.DataFrame(rows, columns=DEFAULT_COLUMN_ORDER)


def explode_pause_features(metadata: Iterable[dict]) -> pd.DataFrame:
    pauses = [event for event in metadata if event.get("pause_events")]
    return pd.DataFrame(pauses)


def compute_typing_metrics(row: pd.Series) -> pd.Series:
    metadata = row["typing_metadata_json"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    keystrokes = metadata.get("keystroke_events", [])
    duration_ms = metadata.get("total_duration_ms", 1) or 1
    words = len(row["user_prompt_text"].split())
    words_per_minute = (words / duration_ms) * 60000
    return pd.Series({
        "keystroke_count": len(keystrokes),
        "duration_ms": duration_ms,
        "words_per_minute": round(words_per_minute, 2)
    })
