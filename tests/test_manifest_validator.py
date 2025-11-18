from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from kitchen.manifests import ManifestValidationReport, validate_manifest_payload
from scripts import manifest_validator


def _manifest_record() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "demo-tenant/welcome-control@3",
        "tenant": "demo-tenant",
        "playground": "welcome-control",
        "revision": 3,
        "revision_label": "ops-demo",
        "cookbook": "Welcome Cookbook",
        "recipe": "control_center_playground",
        "author": "Ops Kitchen",
        "notes": "Story manifest",
        "checksum": "e3c1c7f0f4ad96cf9a4df9fd6f8a93b1",
        "created_at": now,
        "updated_at": now,
        "manifest": {
            "metadata": {"hero": "Control center preview"},
            "layout": {
                "sections": [
                    {
                        "id": "intel",
                        "title": "Intel",
                        "widgets": [
                            {"id": "ru", "type": "stat-card", "title": "RU burn"},
                            {"id": "latency", "type": "stat-card", "title": "LLM latency"},
                        ],
                    }
                ]
            },
            "actions": [
                {"id": "deploy", "title": "Deploy", "route": "/api/deploy", "method": "POST"}
            ],
        },
    }


def test_validate_manifest_record_success() -> None:
    payload = _manifest_record()
    report, errors = validate_manifest_payload(payload)
    assert errors == []
    assert report is not None
    assert report.payload_type == "record"
    assert report.sections == 1
    assert report.widgets == 2
    assert report.actions == 1
    assert report.metadata_keys == ["hero"]
    assert report.tenant == "demo-tenant"
    assert report.playground == "welcome-control"


def test_validate_manifest_body_only() -> None:
    payload = _manifest_record()["manifest"]
    report, errors = validate_manifest_payload(payload)
    assert errors == []
    assert report is not None
    assert report.payload_type == "manifest"
    assert report.sections == 1


def test_validate_manifest_expectation_mismatch() -> None:
    payload = _manifest_record()
    report, errors = validate_manifest_payload(payload, expect_tenant="other")
    assert report is None
    assert "Tenant mismatch" in errors[0]


def test_validate_manifest_rejects_invalid_widget() -> None:
    broken = _manifest_record()
    broken["manifest"]["layout"]["sections"][0]["widgets"][0].pop("type")
    report, errors = validate_manifest_payload(broken)
    assert report is None
    assert any("widgets.0.type" in error for error in errors)


def test_cli_outputs_json(tmp_path: Path, capsys) -> None:
    payload = _manifest_record()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    exit_code = manifest_validator.main([str(manifest_path), "--json"])
    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert isinstance(output, list)
    assert output[0]["path"].endswith("manifest.json")


def test_cli_directory_validation(tmp_path: Path, capsys) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps(_manifest_record()), encoding="utf-8")

    broken_payload = _manifest_record()
    broken_payload["manifest"]["layout"]["sections"][0]["widgets"][0].pop("type")
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(broken_payload), encoding="utf-8")

    exit_code = manifest_validator.main([str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "invalid.json" in captured.err


def test_cli_json_multiple_outputs(tmp_path: Path, capsys) -> None:
    record = _manifest_record()
    file_one = tmp_path / "one.json"
    file_one.write_text(json.dumps(record), encoding="utf-8")
    file_two = tmp_path / "two.json"
    file_two.write_text(json.dumps(record["manifest"]), encoding="utf-8")

    exit_code = manifest_validator.main([str(file_one), str(file_two), "--json"])
    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert {Path(entry["path"]).name for entry in output} == {"one.json", "two.json"}
