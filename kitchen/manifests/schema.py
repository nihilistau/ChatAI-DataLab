from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AllowedSpan = Literal["full", "half", "third"]


class PlaygroundManifestWidget(BaseModel):
	id: str | None = None
	type: str = Field(..., min_length=2)
	title: str | None = None
	props: dict[str, Any] | None = None


class PlaygroundManifestSection(BaseModel):
	id: str | None = None
	title: str | None = None
	description: str | None = None
	accent: str | None = None
	span: AllowedSpan | None = None
	widgets: list[PlaygroundManifestWidget] = Field(default_factory=list)


class PlaygroundManifestLayout(BaseModel):
	sections: list[PlaygroundManifestSection] = Field(default_factory=list)


class PlaygroundManifestAction(BaseModel):
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


class PlaygroundManifestModel(BaseModel):
	version: int | None = None
	metadata: dict[str, Any] | None = None
	layout: PlaygroundManifestLayout | None = None
	actions: list[PlaygroundManifestAction] = Field(default_factory=list)


class PlaygroundManifestRecordModel(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: str
	tenant: str
	playground: str
	revision: int = Field(..., ge=1)
	revision_label: str | None = Field(default=None, alias="revisionLabel")
	cookbook: str | None = None
	recipe: str | None = None
	author: str | None = None
	notes: str | None = None
	checksum: str = Field(..., min_length=8)
	created_at: datetime
	updated_at: datetime
	manifest: PlaygroundManifestModel


__all__ = [
	"PlaygroundManifestAction",
	"PlaygroundManifestLayout",
	"PlaygroundManifestModel",
	"PlaygroundManifestRecordModel",
	"PlaygroundManifestSection",
	"PlaygroundManifestWidget",
]
