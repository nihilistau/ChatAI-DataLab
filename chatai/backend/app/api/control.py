from __future__ import annotations

"""Control Center endpoints powering the Playground widgets."""

# @tag:backend,api,control

from math import sin
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import (
    ControlWidgetResponse,
    LogTailResponse,
    NotebookJobRead,
    NotebookRunRequest,
    OpsStatus,
)
from ..services.notebook_runner import NotebookRunner, get_notebook_runner
from ..services.orchestrator import get_orchestrator

router = APIRouter(prefix="/control", tags=["control"])


def _sparkline_points(length: int, base: float, amplitude: float, offset: float) -> list[float]:
    return [round(base + amplitude * sin((idx + offset) / 2.5), 2) for idx in range(length)]


def _build_widgets_payload() -> ControlWidgetResponse:
    latency_points = _sparkline_points(16, 850, 90, 0)
    ru_points = _sparkline_points(12, 60, 8, 1.3)
    throughput_points = _sparkline_points(16, 4200, 600, 0.8)

    metrics = [
        {
            "id": "latency",
            "label": "LLM Latency",
            "value": latency_points[-1],
            "change_pct": round(((latency_points[-1] - latency_points[-4]) / latency_points[-4]) * 100, 2),
            "unit": "ms",
        },
        {
            "id": "ru-burn",
            "label": "RU Burn",
            "value": ru_points[-1],
            "change_pct": round(((ru_points[-1] - ru_points[-4]) / ru_points[-4]) * 100, 2),
            "unit": "RU/s",
        },
        {
            "id": "keystrokes",
            "label": "Keystrokes Captured",
            "value": throughput_points[-1],
            "change_pct": round(((throughput_points[-1] - throughput_points[-4]) / throughput_points[-4]) * 100, 2),
            "unit": "events/min",
        },
    ]

    payload: dict[str, Any] = {
        "generated_at": datetime.utcnow(),
        "metrics": metrics,
        "sparklines": {
            "latency": latency_points,
            "ru": ru_points,
            "throughput": throughput_points,
        },
    }
    total_budget = 120000.0
    consumed = sum(max(0.0, point) for point in ru_points)
    payload["ru_budget"] = {
        "total": total_budget,
        "consumed": consumed,
        "remaining": max(0.0, total_budget - consumed),
    }
    return ControlWidgetResponse.model_validate(payload)


def get_notebook_runner_dep() -> NotebookRunner:
    return get_notebook_runner()


@router.get("/status", response_model=OpsStatus)
def get_control_status(
    include_logs: bool = Query(False, description="Include log tails for each service"),
    log_lines: int = Query(60, ge=10, le=500),
):
    snapshot = get_orchestrator().snapshot(include_logs=include_logs)
    logs = snapshot.get("logs") or {}
    if include_logs:
        snapshot["logs"] = {name: lines[-log_lines:] for name, lines in logs.items()}
    else:
        snapshot["logs"] = {}
    return snapshot


@router.get("/logs", response_model=LogTailResponse)
def get_service_logs(
    service: str = Query(..., pattern="^(backend|frontend|datalab|playground)$"),
    lines: int = Query(120, ge=10, le=400),
):
    snapshot = get_orchestrator().snapshot(include_logs=True)
    logs = snapshot.get("logs") or {}
    if service not in logs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No log file for service '{service}'")
    return {"service": service, "lines": logs[service][-lines:]}


@router.get("/widgets", response_model=ControlWidgetResponse)
def get_widget_metrics() -> ControlWidgetResponse:
    return _build_widgets_payload()


@router.get("/notebooks", response_model=list[NotebookJobRead])
async def list_notebook_runs(runner: NotebookRunner = Depends(get_notebook_runner_dep)):
    return [NotebookJobRead.model_validate(job.to_dict()) for job in runner.list_jobs()]


@router.post("/notebooks", response_model=NotebookJobRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_notebook_run(
    payload: NotebookRunRequest,
    runner: NotebookRunner = Depends(get_notebook_runner_dep),
):
    try:
        job = await runner.submit(payload.name, payload.parameters)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NotebookJobRead.model_validate(job.to_dict())
