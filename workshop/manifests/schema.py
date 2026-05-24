from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AllowedSpan = Literal["full", "half", "third"]


class RelayManifestWidget(BaseModel):
	id: str | None = None
	type: str = Field(..., min_length=2)
	title: str | None = None
	props: dict[str, Any] | None = None


class RelayManifestSection(BaseModel):
	id: str | None = None
	title: str | None = None
	description: str | None = None
	accent: str | None = None
	span: AllowedSpan | None = None
	widgets: list[RelayManifestWidget] = Field(default_factory=list)


class RelayManifestLayout(BaseModel):
	sections: list[RelayManifestSection] = Field(default_factory=list)


class RelayManifestAction(BaseModel):
	id: str | None = None
	title: str | None = None
	route: str = Field(..., min_length=1)
	method: str = Field(default="POST", min_length=2)
	description: str | None = None

	@field_validator("route")
	@classmethod
	def validate_route(cls, value: str) -> str:  # type: ignore[override]
		if not value.startswith("/") and not value.startswith("http"):
			raise ValueError("route must start with '/' or an absolute URL")
		return value


class RelayManifestModel(BaseModel):
	version: int | None = None
	metadata: dict[str, Any] | None = None
	layout: RelayManifestLayout | None = None
	actions: list[RelayManifestAction] = Field(default_factory=list)


class RelayManifestRecordModel(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: str
	tenant: str
	relay: str
	revision: int = Field(..., ge=1)
	revision_label: str | None = Field(default=None, alias="revisionLabel")
	cookbook: str | None = None
	recipe: str | None = None
	author: str | None = None
	notes: str | None = None
	checksum: str = Field(..., min_length=8)
	created_at: datetime
	updated_at: datetime
	manifest: RelayManifestModel


__all__ = [
	"RelayManifestAction",
	"RelayManifestLayout",
	"RelayManifestModel",
	"RelayManifestRecordModel",
	"RelayManifestSection",
	"RelayManifestWidget",
]
