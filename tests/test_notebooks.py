from __future__ import annotations

"""Papermill smoke tests for DataLab notebooks."""

# @tag: datalab,tests,notebooks

from pathlib import Path
import sqlite3

import papermill as pm
import pytest

from tests.utils.notebooks import normalize_notebook

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime\\.datetime\\.utcnow\\(\\) is deprecated.*:DeprecationWarning:papermill.*",
    "ignore:Cell is missing an id field.*:nbformat.validator.MissingIDFieldWarning",
)

NOTEBOOK_DIR = Path(__file__).resolve().parents[1] / "datalab" / "notebooks"
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


@pytest.mark.parametrize(
    "notebook_name",
    [
        "quickstart.ipynb",
        "hypothesis_control.ipynb",
        "control_center_playground.ipynb",
    ],
)
def test_notebooks_execute(notebook_name: str, tmp_path: Path) -> None:
    notebook_path = NOTEBOOK_DIR / notebook_name
    normalized_notebook = normalize_notebook(notebook_path, tmp_path / notebook_name)
    output_path = OUTPUT_DIR / f"{notebook_name.replace('.ipynb', '')}-executed.ipynb"

    sample_db = tmp_path / "interactions.db"
    _create_sample_db(sample_db)

    pm.execute_notebook(
        str(normalized_notebook),
        str(output_path),
        parameters={"DB_PATH": str(sample_db)},
        kernel_name="python3",
        cwd=NOTEBOOK_DIR,
        log_output=True,
    )
