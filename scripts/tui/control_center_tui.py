#!/usr/bin/env python3
"""Textual TUI for browsing release + tail logs without opening the full UI."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Footer, Header, Static, TextLog

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("LAB_ROOT", str(ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relay.backend.app.services.data_store import data_store_context
from relay.backend.app.services.release_log import list_release_log_entries
from scripts.ops_telemetry import telemetry_span

TELEMETRY_SKIP_KEYS = {
    "skip_tail_log",
    "skip_release_log",
    "tail_log_source",
    "release_log_kind",
    "release_log_path",
}


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _coerce_value(value: Any) -> Any:
    if isinstance(value, Path):
        return _relativize(value)
    if isinstance(value, list):
        return [_coerce_value(item) for item in value]
    return value


def _sanitize_args(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in vars(args).items():
        if key in TELEMETRY_SKIP_KEYS:
            continue
        payload[key] = _coerce_value(value)
    return payload


def _tail_entry_to_dict(entry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "source": entry.source,
        "message": entry.message,
        "created_at": entry.created_at.isoformat(),
    }


class ControlCenterDataProvider:
    """Blocking data accessors suitable for running inside worker threads."""

    def __init__(self, release_limit: int, tail_limit: int) -> None:
        self.release_limit = release_limit
        self.tail_limit = tail_limit

    def snapshot(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        releases = list_release_log_entries(self.release_limit)
        with data_store_context() as store:
            tail_records = store.list_tail_log(limit=self.tail_limit)
        tails = [_tail_entry_to_dict(entry) for entry in tail_records]
        return releases, tails


class ControlCenterTUI(App):
    CSS = """
    Screen {
        layout: vertical;
        background: #05060a;
        color: #f5f5f5;
    }
    #log-row {
        height: 1fr;
    }
    #release-pane, #tail-pane {
        width: 1fr;
        padding: 1;
    }
    TextLog {
        height: 1fr;
        border: solid #1f2030;
        background: #090b12;
    }
    #status-line {
        padding: 1;
        border-top: solid #1f2030;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh data"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        provider: ControlCenterDataProvider,
        *,
        auto_refresh: float,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.auto_refresh_seconds = auto_refresh
        self._auto_refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="log-row"):
            with Vertical(id="release-pane"):
                yield Static("Release Log", id="release-title")
                yield TextLog(id="release-log", highlight=False, markup=False, wrap=True)
            with Vertical(id="tail-pane"):
                yield Static("Tail Log", id="tail-title")
                yield TextLog(id="tail-log", highlight=False, markup=False, wrap=True)
            yield Static("Waiting for first refresh…", id="status-line")
        yield Footer()

    async def on_mount(self) -> None:
        if self.auto_refresh_seconds > 0:
            self._auto_refresh_timer = self.set_interval(
                self.auto_refresh_seconds,
                self._auto_refresh_tick,
                pause=False,
            )
        await self.refresh_dashboard(initial=True)

    async def on_unmount(self) -> None:
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()

    async def _auto_refresh_tick(self) -> None:
        await self.refresh_dashboard()

    async def action_refresh(self) -> None:
        await self.refresh_dashboard()

    async def refresh_dashboard(self, *, initial: bool = False) -> None:
        status = "Initializing" if initial else "Refreshing"
        self._set_status(f"{status}…")
        try:
            releases, tails = await self.call_in_thread(self.provider.snapshot)
        except Exception as exc:  # pragma: no cover - surface error to UI
            self._set_status(f"Error fetching data: {exc}")
            raise
        self._populate_release_log(releases)
        self._populate_tail_log(tails)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        refresh_note = (
            f"Last refresh {ts} · releases={len(releases)} · tails={len(tails)} · press [r] to refresh"
        )
        if self.auto_refresh_seconds > 0:
            refresh_note += f" · auto every {self.auto_refresh_seconds:.0f}s"
        self._set_status(refresh_note)

    def _populate_release_log(self, entries: list[dict[str, Any]]) -> None:
        widget = self.query_one("#release-log", TextLog)
        widget.clear()
        if not entries:
            widget.write("No release log entries yet.")
            return
        for entry in entries:
            widget.write(self._format_release_entry(entry))
            for step in entry.get("timeline", []) or []:
                name = step.get("name", "step")
                status = step.get("status", "?")
                details = step.get("details")
                line = f"   • {name} · {status}"
                if details:
                    line += f" · {details}"
                widget.write(line)
            widget.write("")

    def _populate_tail_log(self, entries: list[dict[str, Any]]) -> None:
        widget = self.query_one("#tail-log", TextLog)
        widget.clear()
        if not entries:
            widget.write("Tail log empty.")
            return
        for entry in entries:
            widget.write(self._format_tail_entry(entry))

    def _format_release_entry(self, entry: dict[str, Any]) -> str:
        timestamp = entry.get("timestamp") or "?"
        status = entry.get("status") or entry.get("overall") or "unknown"
        kind = entry.get("kind")
        summary = entry.get("summary") or entry.get("action") or "(no summary)"
        duration = entry.get("duration_seconds")
        suffix = f" · {duration:.1f}s" if isinstance(duration, (int, float)) else ""
        return f"[{timestamp}] {status} · {kind or 'release'} · {summary}{suffix}"

    def _format_tail_entry(self, entry: dict[str, Any]) -> str:
        timestamp = entry.get("created_at") or "?"
        source = entry.get("source", "tail")
        message = entry.get("message", "")
        return f"[{timestamp}] {source}: {message}"

    def _set_status(self, message: str) -> None:
        self.query_one("#status-line", Static).update(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control Center Textual dashboard")
    parser.add_argument("--release-limit", type=int, default=8, help="How many release log rows to display")
    parser.add_argument("--tail-limit", type=int, default=20, help="How many tail log rows to display")
    parser.add_argument(
        "--auto-refresh",
        type=float,
        default=0.0,
        help="Optional auto-refresh interval in seconds (0 disables)",
    )
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="control-center-tui", help="Tail log source label")
    parser.add_argument("--release-log-kind", default="control_center_tui", help="Release log kind label")
    parser.add_argument("--release-log-path", default=None, help="Optional release log override path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    provider = ControlCenterDataProvider(args.release_limit, args.tail_limit)
    sanitized_args = _sanitize_args(args)
    state = {"status": "pending"}

    def _tail_message() -> str:
        return f"control_center_tui {state['status']} · releases={args.release_limit} · tails={args.tail_limit}"

    release_entry = {
        "kind": "control_center_tui",
        "action": "tui",
        "args": sanitized_args,
    }
    release_details = {"args": sanitized_args}

    with telemetry_span(
        "control-center-tui",
        component="control_center_tui",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary="Control Center TUI",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as recorder:
        try:
            app = ControlCenterTUI(provider=provider, auto_refresh=args.auto_refresh)
            app.run()
        except KeyboardInterrupt:
            state["status"] = "cancelled"
            recorder.record_step("tui", status="cancelled", details={"reason": "KeyboardInterrupt"})
            recorder.set_metadata(status="cancelled")
            release_entry["status"] = "cancelled"
            return 0
        except Exception as exc:
            state["status"] = "failed"
            recorder.record_step("tui", status="failed", details={"error": str(exc)})
            release_entry["error"] = str(exc)
            recorder.set_metadata(status="failed")
            raise
        state["status"] = "completed"
        recorder.record_step(
            "tui",
            status="ok",
            details={"release_limit": args.release_limit, "tail_limit": args.tail_limit},
        )
        recorder.set_metadata(status="ok", release_limit=args.release_limit, tail_limit=args.tail_limit)
        release_entry["status"] = "ok"
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
