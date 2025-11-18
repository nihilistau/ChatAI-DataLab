from __future__ import annotations

"""Papermill smoke tests for Kitchen notebooks."""

# @tag: kitchen,tests,notebooks

import json
from pathlib import Path
import sqlite3

import papermill as pm
import pytest

from tests.utils.notebooks import normalize_notebook
from kitchen.scripts import search_telemetry

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime\\.datetime\\.utcnow\\(\\) is deprecated.*:DeprecationWarning:papermill.*",
    "ignore:Cell is missing an id field.*:nbformat.validator.MissingIDFieldWarning",
)

NOTEBOOK_DIR = Path(__file__).resolve().parents[1] / "kitchen" / "notebooks"
OUTPUT_DIR = NOTEBOOK_DIR / "_papermill"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _create_sample_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                user_prompt_text TEXT,
                typing_metadata_json TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            "DELETE FROM interactions"
        )
        conn.executemany(
            "INSERT INTO interactions VALUES (?, ?, ?, ?)",
            [
                (
                    "prompt-001",
                    "Quickstart prompt",
                    '{"total_duration_ms": 1500, "keystroke_events": [], "pause_events": []}',
                    "2025-01-01T00:00:00Z",
                ),
                (
                    "prompt-002",
                    "Follow-up",
                    '{"total_duration_ms": 900, "keystroke_events": [{"key": "a"}], "pause_events": []}',
                    "2025-01-02T00:00:00Z",
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def _create_sample_search_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = db_path.parent / "search-history.jsonl"
    sample_entries = [
        {
            "timestamp": "2025-11-15T12:00:00Z",
            "pattern": "TODO",
            "preset": "todo-scan",
            "regex": False,
            "caseSensitive": False,
            "root": "./",
            "recursive": True,
            "includeFiles": ["*.py"],
            "excludePatterns": ["node_modules"],
            "filesScanned": 5,
            "matches": 2,
            "durationMs": 150,
        },
        {
            "timestamp": "2025-11-16T08:30:00Z",
            "pattern": "FIXME",
            "preset": "todo-scan",
            "regex": False,
            "caseSensitive": False,
            "root": "./",
            "recursive": True,
            "includeFiles": ["*.ts"],
            "excludePatterns": ["storybook"],
            "filesScanned": 3,
            "matches": 0,
            "durationMs": 90,
        },
    ]
    with log_path.open("w", encoding="utf-8") as handle:
        for entry in sample_entries:
            handle.write(json.dumps(entry) + "\n")

    search_telemetry.ingest_search_history(log_path, db_path)


@pytest.mark.parametrize(
    "notebook_name",
    [
        "quickstart.ipynb",
        "hypothesis_control.ipynb",
        "control_center_playground.ipynb",
        "elements_playground.ipynb",
        "elements_reporting.ipynb",
        "search_telemetry.ipynb",
    ],
)
def test_notebooks_execute(notebook_name: str, tmp_path: Path) -> None:
    notebook_path = NOTEBOOK_DIR / notebook_name
    normalized_notebook = normalize_notebook(notebook_path, tmp_path / notebook_name)
    output_path = OUTPUT_DIR / f"{notebook_name.replace('.ipynb', '')}-executed.ipynb"

    sample_db = tmp_path / "interactions.db"
    _create_sample_db(sample_db)
    sample_search_db = tmp_path / "search_telemetry.json"
    _create_sample_search_db(sample_search_db)

    pm.execute_notebook(
        str(normalized_notebook),
        str(output_path),
        parameters={
            "DB_PATH": str(sample_db),
            "SEARCH_LEDGER_PATH": str(sample_search_db),
        },
        kernel_name="python3",
        cwd=NOTEBOOK_DIR,
        log_output=True,
    )
