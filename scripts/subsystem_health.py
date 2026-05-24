#!/usr/bin/env python
"""Quick automation to capture manifest + telemetry health snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workshop.manifests import validate_manifest_payload
from scripts.ops_telemetry import telemetry_span

DEFAULT_MANIFEST_TARGETS = (
    REPO_ROOT / "manifests",
    REPO_ROOT / "workshop" / "manifests",
    REPO_ROOT / "legacy" / "archives" / "manifests",
)
SNAPSHOT_PATH = REPO_ROOT / "workshop" / "notebooks" / "_papermill" / "control_center_snapshot.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "subsystem_health.json"


@dataclass
class ManifestResult:
    path: str
    sections: int
    widgets: int
    actions: int
    tenant: str | None
    relay: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _iter_manifest_files(targets: Iterable[Path], pattern: str) -> Iterator[Path]:
    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            yield target
            continue
        if target.is_dir():
            yield from sorted(p for p in target.rglob(pattern) if p.is_file())


def _scan_manifests(targets: Iterable[Path], pattern: str) -> tuple[list[ManifestResult], list[str]]:
    summaries: list[ManifestResult] = []
    errors: list[str] = []
    for manifest_path in _iter_manifest_files(targets, pattern):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{manifest_path}: {exc}")
            continue
        report, report_errors = validate_manifest_payload(payload)
        if report_errors or report is None:
            for err in report_errors:
                errors.append(f"{manifest_path}: {err}")
            continue
        summaries.append(
            ManifestResult(
                path=str(manifest_path.relative_to(REPO_ROOT)),
                sections=report.sections,
                widgets=report.widgets,
                actions=report.actions,
                tenant=report.tenant,
                relay=report.relay,
            )
        )
    return summaries, errors


def _load_snapshot() -> dict[str, object] | None:
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate subsystem health signals into a JSON report")
    parser.add_argument("--pattern", default="*.json", help="Glob used when scanning manifest directories")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Report destination (JSON)")
    parser.add_argument(
        "--include",
        nargs="*",
        default=[str(path) for path in DEFAULT_MANIFEST_TARGETS],
        help="Additional directories/files (defaults cover manifests/, workshop/manifests, legacy/archives/manifests)",
    )
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument("--tail-log-source", default="subsystem-health", help="Tail log source label")
    parser.add_argument(
        "--release-log-kind",
        default="subsystem_health",
        help="Kind label recorded in release log entries",
    )
    parser.add_argument(
        "--release-log-path",
        default=None,
        help="Optional override for the release log location",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    release_entry = {
        "kind": "subsystem_health",
        "action": "subsystem_health",
        "pattern": args.pattern,
        "output": args.output,
    }
    release_details = {
        "pattern": args.pattern,
        "include": args.include,
    }

    summaries: list[ManifestResult] = []
    errors: list[str] = []
    snapshot: dict[str, object] | None = None
    output_payload: dict[str, Any] | None = None
    output_path: Path | None = None

    def _tail_message() -> str:
        location = str(output_path) if output_path else args.output
        status = "ok" if not errors else "with-errors" if errors else "pending"
        return f"subsystem health · status={status} · output={location}"

    with telemetry_span(
        "subsystem-health",
        component="subsystem_health",
        tail_source=args.tail_log_source,
        tail_message=_tail_message,
        release_kind=args.release_log_kind,
        release_log_path=args.release_log_path,
        release_summary="Subsystem health snapshot",
        release_details=release_details,
        release_entry=release_entry,
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as span:
        targets = [Path(path).expanduser().resolve() for path in args.include]
        summaries, errors = _scan_manifests(targets, pattern=args.pattern)

        snapshot = _load_snapshot()
        output_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "manifest_results": [summary.as_dict() for summary in summaries],
            "manifest_errors": errors,
            "control_center_snapshot": snapshot,
        }

        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

        scan_status = "ok" if not errors else "failed"
        span.record_step(
            "manifest_scan",
            status=scan_status,
            details={"valid": len(summaries), "errors": len(errors)},
        )
        span.record_step(
            "snapshot",
            status="ok" if snapshot else "skipped",
            details={"has_snapshot": bool(snapshot)},
        )
        span.record_step(
            "write_report",
            status="ok",
            details={"output": str(output_path)},
        )
        span.set_metadata(
            manifest_count=len(summaries),
            error_count=len(errors),
            output=str(output_path),
        )

        release_entry.update(
            {
                "manifest_count": len(summaries),
                "error_count": len(errors),
                "snapshot_present": bool(snapshot),
            }
        )

    success_label = "ok" if not errors else "with-errors"
    print(f"Manifest scan ({success_label}): {len(summaries)} valid, {len(errors)} errors")
    if snapshot:
        services = ", ".join(snapshot.get("service_states", [])) or "n/a"
        print(f"Control Center snapshot: prompts={snapshot.get('prompt_count', 'n/a')} services={services}")
    else:
        print("Control Center snapshot: not found")
    output_display = str(output_path) if output_path else args.output
    print(f"Report written to {output_display}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
