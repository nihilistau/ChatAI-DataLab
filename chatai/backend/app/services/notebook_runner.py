from __future__ import annotations

"""Async notebook execution helper backed by Papermill."""

# @tag:backend,services,notebooks

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional
import asyncio
import uuid

NotebookStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class NotebookJob:
    id: str
    name: str
    status: NotebookStatus = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # Dataclass -> dict retains datetime objects; FastAPI handles serialization.
        return payload


class NotebookRunner:
    """Dispatch notebooks via Papermill using a background asyncio task."""

    def __init__(
        self,
        notebooks_dir: Path | None = None,
        *,
        executor: Callable[[Path, Path, Dict[str, Any]], None] | None = None,
    ) -> None:
        self.notebooks_dir = Path(notebooks_dir or Path(__file__).resolve().parents[3] / "datalab" / "notebooks")
        self.output_dir = self.notebooks_dir / "_papermill"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, NotebookJob] = {}
        self._executor = executor or self._papermill_execute
        self._lock = asyncio.Lock()

    def list_jobs(self) -> List[NotebookJob]:
        # Return newest first for dashboards.
        return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    async def submit(self, name: str, parameters: Optional[Dict[str, Any]] = None) -> NotebookJob:
        notebook_path = self.notebooks_dir / name
        if not notebook_path.exists():
            raise FileNotFoundError(f"Notebook '{name}' not found under {self.notebooks_dir}")

        job_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"{name.replace('.ipynb', '')}-{timestamp}.ipynb"
        job = NotebookJob(
            id=job_id,
            name=name,
            parameters=parameters or {},
            output_path=str(output_path),
        )
        self._jobs[job_id] = job

        loop = asyncio.get_running_loop()
        loop.create_task(self._execute_job(job, notebook_path, output_path))
        return job

    async def _execute_job(self, job: NotebookJob, notebook_path: Path, output_path: Path) -> None:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        try:
            await asyncio.to_thread(self._executor, notebook_path, output_path, job.parameters)
            job.status = "succeeded"
        except Exception as exc:  # pragma: no cover - surfaced via API
            job.status = "failed"
            job.error = str(exc)
        finally:
            job.completed_at = datetime.now(timezone.utc)

    @staticmethod
    def _papermill_execute(notebook_path: Path, output_path: Path, parameters: Dict[str, Any]) -> None:
        import papermill as pm  # Lazy import so backend boots without Papermill until first run

        pm.execute_notebook(
            str(notebook_path),
            str(output_path),
            parameters=parameters or {},
            cwd=notebook_path.parent,
            progress_bar=False,
        )


_NOTEBOOK_RUNNER: NotebookRunner | None = None


def get_notebook_runner() -> NotebookRunner:
    global _NOTEBOOK_RUNNER
    if _NOTEBOOK_RUNNER is None:
        _NOTEBOOK_RUNNER = NotebookRunner()
    return _NOTEBOOK_RUNNER


def set_notebook_runner(runner: NotebookRunner | None) -> None:
    global _NOTEBOOK_RUNNER
    _NOTEBOOK_RUNNER = runner
