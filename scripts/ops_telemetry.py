#!/usr/bin/env python3
"""Shared telemetry helpers for CLI workflows and automation scripts."""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relay.backend.app.config import get_settings
from relay.backend.app.schemas import TailLogEntryCreate
from relay.backend.app.services.data_store import data_store_context

DEFAULT_TAIL_SOURCE = "ops-cli"
DEFAULT_RELEASE_KIND = "ops_cli"
DEFAULT_COMPONENT = "ops_cli"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _release_log_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    if explicit:
        return Path(explicit)
    env_override = os.environ.get("RELEASE_LOG_PATH")
    if env_override:
        return Path(env_override)
    settings = get_settings()
    return settings.release_log_path


def emit_tail_log(message: str, *, source: str = DEFAULT_TAIL_SOURCE) -> None:
    """Persist a tail log entry via the shared data store."""

    try:
        with data_store_context() as store:
            store.create_tail_log_entry(TailLogEntryCreate(message=message, source=source))
    except Exception as exc:  # pragma: no cover - defensive guardrail
        print(f"[ops-telemetry] tail log emission failed: {exc}", file=sys.stderr)


def append_release_log(entry: dict[str, Any], *, path: str | os.PathLike[str] | None = None) -> None:
    """Append a structured entry to data/logs/release.log."""

    target = _release_log_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str))
        handle.write("\n")


@dataclass
class TelemetryStep:
    name: str
    status: str = "ok"
    details: Any | None = None
    duration_seconds: float | None = None
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())


@dataclass
class TelemetryRecorder:
    action: str
    component: str
    timeline: list[TelemetryStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_step(
        self,
        name: str,
        *,
        status: str = "ok",
        details: Any | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        self.timeline.append(
            TelemetryStep(
                name=name,
                status=status,
                details=details,
                duration_seconds=duration_seconds,
            )
        )

    def set_metadata(self, **kwargs: Any) -> None:
        self.metadata.update(kwargs)


@contextmanager
def telemetry_span(
    action: str,
    *,
    component: str = DEFAULT_COMPONENT,
    tail_source: str = DEFAULT_TAIL_SOURCE,
    tail_message: str | Callable[[], str] | None = None,
    release_kind: str | None = None,
    release_log_path: str | os.PathLike[str] | None = None,
    release_summary: str | None = None,
    release_details: dict[str, Any] | None = None,
    release_entry: dict[str, Any] | None = None,
    skip_tail_log: bool = False,
    skip_release_log: bool = False,
) -> Iterator[TelemetryRecorder]:
    """Context manager that wires telemetry for CLI/automation actions."""

    recorder = TelemetryRecorder(action=action, component=component)
    started = _utc_now()
    status = "ok"
    error_details: str | None = None

    try:
        yield recorder
    except Exception as exc:
        status = "failed"
        error_details = str(exc)
        raise
    finally:
        finished = _utc_now()
        duration = round((finished - started).total_seconds(), 3)
        if not skip_tail_log:
            message_value: str | None = None
            if callable(tail_message):
                try:
                    message_value = tail_message()
                except Exception as exc:  # pragma: no cover - defensive guardrail
                    message_value = f"{component} · {action} {status} ({exc})"
            else:
                message_value = tail_message
            message = message_value or f"{component} · {action} {status}"
            if status == "failed" and error_details:
                message = f"{message} — {error_details}"[:360]
            elif duration is not None:
                message = f"{message} ({duration:.1f}s)"
            emit_tail_log(message, source=tail_source)
        if not skip_release_log:
            entry = {
                "timestamp": finished.isoformat(),
                "kind": release_kind or component,
                "action": action,
                "status": status,
                "source": tail_source,
                "duration_seconds": duration,
                "summary": release_summary,
                "timeline": [step.__dict__ for step in recorder.timeline],
            }
            if error_details:
                entry["error"] = error_details
            if release_details:
                entry["details"] = release_details
            if recorder.metadata:
                entry["metadata"] = recorder.metadata
            if release_entry:
                entry.update(release_entry)
            append_release_log(entry, path=release_log_path)


__all__ = [
    "append_release_log",
    "emit_tail_log",
    "telemetry_span",
    "TelemetryRecorder",
]
