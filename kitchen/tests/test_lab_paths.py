from __future__ import annotations

import importlib
from pathlib import Path

import kitchen.lab_paths as lab_paths
from kitchen import diagnostics


def test_lab_root_honors_environment(monkeypatch, tmp_path):
	repo_root = tmp_path / "lab"
	repo_root.mkdir()
	monkeypatch.setenv("LAB_ROOT", str(repo_root))

	importlib.reload(lab_paths)

	assert lab_paths.get_lab_root() == repo_root
	data_target = lab_paths.data_path("interactions.db")
	assert data_target == repo_root / "data" / "interactions.db"


def test_record_run_metadata(tmp_path, monkeypatch):
	repo_root = tmp_path / "lab"
	notebook_dir = repo_root / "kitchen" / "_papermill"
	notebook_dir.mkdir(parents=True)
	monkeypatch.setenv("LAB_ROOT", str(repo_root))

	importlib.reload(lab_paths)
	importlib.reload(diagnostics)

	metadata = diagnostics.record_run_metadata(parameters={"db_path": "example"})
	metadata_path = Path(diagnostics.DEFAULT_METADATA_PATH)
	assert metadata_path.exists()
	assert metadata["db_path"] == "example"
	assert metadata["lab_root"] == str(repo_root)
