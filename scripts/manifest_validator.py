from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ops_telemetry import telemetry_span, TelemetryRecorder
from workshop.manifests import ManifestValidationReport, validate_manifest_payload


def _iter_payloads(source: str, pattern: str) -> Iterator[tuple[str, Any]]:
    if source == "-":
        yield ("<stdin>", json.load(sys.stdin))
        return

    path = Path(source)
    if path.is_dir():
        matched = sorted(p for p in path.rglob(pattern) if p.is_file())
        if not matched:
            raise FileNotFoundError(f"No files matching {pattern!r} under {path}")
        for candidate in matched:
            with candidate.open("r", encoding="utf-8") as handle:
                yield (str(candidate), json.load(handle))
        return

    with path.open("r", encoding="utf-8") as handle:
        yield (str(path), json.load(handle))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a Relay manifest JSON payload")
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more manifest JSON files, directories, or '-' to read from stdin",
    )
    parser.add_argument("--expect-tenant", dest="expect_tenant", help="Optional tenant expectation")
    parser.add_argument("--expect-relay", dest="expect_relay", help="Optional relay expectation")
    parser.add_argument(
        "--pattern",
        default="*.json",
        help="Glob used when a directory path is supplied (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the validation summary as JSON (useful for MCP integrations)",
    )
    parser.add_argument("--skip-tail-log", action="store_true", help="Disable tail log emission")
    parser.add_argument("--skip-release-log", action="store_true", help="Disable release log emission")
    parser.add_argument(
        "--tail-log-source",
        default="manifest-validator",
        help="Source label recorded in the tail log",
    )
    parser.add_argument(
        "--release-kind",
        default="manifest_validator",
        help="Kind label for release log entries",
    )
    parser.add_argument(
        "--release-log-path",
        default=None,
        help="Optional override for the release log file location",
    )
    return parser


def _print_summary(report: ManifestValidationReport, *, label: str | None = None) -> None:
    header = "✔ Manifest" if report.payload_type == "manifest" else "✔ Manifest record"
    prefix = f"[{label}] " if label else ""
    print(
        f"{prefix}{header} is valid: {report.sections} sections, {report.widgets} widgets, {report.actions} actions"
    )
    if report.tenant and report.relay:
        revision = f" rev {report.revision}" if report.revision is not None else ""
        print(f"{prefix}  Namespace {report.tenant}/{report.relay}{revision}")
    if report.metadata_keys:
        print(f"{prefix}  Metadata keys: {', '.join(report.metadata_keys)}")


def _run_validation(args: argparse.Namespace) -> Tuple[int, dict[str, Any], list[dict[str, Any]]]:
    if "-" in args.paths and len(args.paths) > 1:
        raise SystemExit("'-' (stdin) can only be used alone")

    any_failures = False
    json_results: list[dict[str, Any]] = []
    multiple_inputs = len(args.paths) > 1
    total_payloads = 0
    valid_payloads = 0
    invalid_payloads = 0

    for raw_path in args.paths:
        try:
            payloads = list(_iter_payloads(raw_path, args.pattern))
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - IO failures
            print(f"✖ Unable to load manifest(s) from {raw_path}: {exc}", file=sys.stderr)
            any_failures = True
            invalid_payloads += 1
            continue

        for label, payload in payloads:
            total_payloads += 1
            report, errors = validate_manifest_payload(
                payload,
                expect_tenant=getattr(args, "expect_tenant", None),
                expect_relay=getattr(args, "expect_relay", None),
            )

            if errors or report is None:
                any_failures = True
                invalid_payloads += 1
                for error in errors:
                    print(f"✖ [{label}] {error}", file=sys.stderr)
                continue

            valid_payloads += 1
            if args.json:
                json_results.append({"path": label, **report.as_dict()})
            else:
                _print_summary(report, label=label if multiple_inputs else None)

    stats = {
        "total": total_payloads,
        "valid": valid_payloads,
        "invalid": invalid_payloads,
    }
    exit_code = 1 if any_failures else 0
    return exit_code, stats, json_results


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    release_summary = f"Validated {len(args.paths)} path(s)"
    with telemetry_span(
        "manifest-validator",
        component="manifest_validator",
        tail_source=args.tail_log_source,
        release_kind=args.release_kind,
        release_log_path=args.release_log_path,
        release_summary=release_summary,
        release_details={"paths": args.paths},
        skip_tail_log=args.skip_tail_log,
        skip_release_log=args.skip_release_log,
    ) as span:
        exit_code, stats, json_results = _run_validation(args)
        status = "ok" if exit_code == 0 else "failed"
        span.record_step("validation", status=status, details=stats)
        span.set_metadata(**stats)
        if args.json and json_results:
            print(json.dumps(json_results, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
