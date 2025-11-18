from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kitchen.manifests import ManifestValidationReport, validate_manifest_payload


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
    parser = argparse.ArgumentParser(description="Validate a Playground manifest JSON payload")
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more manifest JSON files, directories, or '-' to read from stdin",
    )
    parser.add_argument("--expect-tenant", dest="expect_tenant", help="Optional tenant expectation")
    parser.add_argument("--expect-playground", dest="expect_playground", help="Optional playground expectation")
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
    return parser


def _print_summary(report: ManifestValidationReport, *, label: str | None = None) -> None:
    header = "✔ Manifest" if report.payload_type == "manifest" else "✔ Manifest record"
    prefix = f"[{label}] " if label else ""
    print(
        f"{prefix}{header} is valid: {report.sections} sections, {report.widgets} widgets, {report.actions} actions"
    )
    if report.tenant and report.playground:
        revision = f" rev {report.revision}" if report.revision is not None else ""
        print(f"{prefix}  Namespace {report.tenant}/{report.playground}{revision}")
    if report.metadata_keys:
        print(f"{prefix}  Metadata keys: {', '.join(report.metadata_keys)}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if "-" in args.paths and len(args.paths) > 1:
        parser.error("'-' (stdin) can only be used alone")

    any_failures = False
    json_results: list[dict[str, Any]] = []
    multiple_inputs = len(args.paths) > 1

    for raw_path in args.paths:
        try:
            payloads = list(_iter_payloads(raw_path, args.pattern))
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - IO failures
            print(f"✖ Unable to load manifest(s) from {raw_path}: {exc}", file=sys.stderr)
            any_failures = True
            continue

        for label, payload in payloads:
            report, errors = validate_manifest_payload(
                payload,
                expect_tenant=getattr(args, "expect_tenant", None),
                expect_playground=getattr(args, "expect_playground", None),
            )

            if errors or report is None:
                any_failures = True
                for error in errors:
                    print(f"✖ [{label}] {error}", file=sys.stderr)
                continue

            if args.json:
                json_results.append({"path": label, **report.as_dict()})
            else:
                _print_summary(report, label=label if multiple_inputs else None)

    if args.json and json_results:
        print(json.dumps(json_results, indent=2))

    return 1 if any_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
