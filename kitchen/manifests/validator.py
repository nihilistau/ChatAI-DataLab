from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Tuple

from pydantic import ValidationError

from .schema import PlaygroundManifestModel, PlaygroundManifestRecordModel

PayloadType = Literal["record", "manifest"]


@dataclass
class ManifestValidationReport:
	payload_type: PayloadType
	sections: int
	widgets: int
	actions: int
	metadata_keys: list[str]
	tenant: str | None = None
	playground: str | None = None
	revision: int | None = None

	def as_dict(self) -> dict[str, Any]:
		return asdict(self)


def validate_manifest_payload(
	payload: Any,
	*,
	expect_tenant: str | None = None,
	expect_playground: str | None = None,
) -> Tuple[ManifestValidationReport | None, list[str]]:
	"""Validate a manifest payload and return a summary + error list."""

	errors: list[str] = []
	record: PlaygroundManifestRecordModel | None = None
	manifest: PlaygroundManifestModel | None = None
	payload_type: PayloadType = "manifest"

	if isinstance(payload, dict) and {"tenant", "playground", "manifest"}.issubset(payload.keys()):
		try:
			record = PlaygroundManifestRecordModel.model_validate(payload)
			manifest = record.manifest
			payload_type = "record"
		except ValidationError as exc:
			return None, _format_errors(exc)

	if manifest is None:
		try:
			manifest = PlaygroundManifestModel.model_validate(payload)
		except ValidationError as exc:
			return None, _format_errors(exc)

	if expect_tenant or expect_playground:
		if record is None:
			errors.append("Expected tenant/playground metadata but payload only contains a manifest body.")
		else:
			if expect_tenant and record.tenant != expect_tenant:
				errors.append(
					f"Tenant mismatch: expected '{expect_tenant}' but manifest targets '{record.tenant}'."
				)
			if expect_playground and record.playground != expect_playground:
				errors.append(
					f"Playground mismatch: expected '{expect_playground}' but manifest targets '{record.playground}'."
				)

	if errors:
		return None, errors

	sections = manifest.layout.sections if manifest.layout else []
	widgets = sum(len(section.widgets) for section in sections)
	actions = len(manifest.actions)
	metadata_keys = sorted(manifest.metadata.keys()) if manifest.metadata else []

	report = ManifestValidationReport(
		payload_type=payload_type,
		sections=len(sections),
		widgets=widgets,
		actions=actions,
		metadata_keys=metadata_keys,
		tenant=record.tenant if record else None,
		playground=record.playground if record else None,
		revision=record.revision if record else None,
	)
	return report, []


def _format_errors(error: ValidationError) -> list[str]:
	formatted: list[str] = []
	for detail in error.errors():
		location = ".".join(str(part) for part in detail.get("loc", ()))
		formatted.append(f"{location or '<root>'}: {detail.get('msg')}")
	return formatted


__all__ = ["ManifestValidationReport", "validate_manifest_payload"]
