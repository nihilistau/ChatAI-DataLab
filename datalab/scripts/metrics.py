"""Reusable helpers for turning typing metadata JSON into analytic features."""
# @tag: datalab,scripts,analytics

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


def load_interactions(db_path: Path) -> pd.DataFrame:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query("SELECT * FROM interactions ORDER BY created_at DESC", conn)
    finally:
        conn.close()


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
