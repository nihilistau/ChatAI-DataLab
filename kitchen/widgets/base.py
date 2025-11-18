"""Core data structures for Kitchen widget + panel rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, Iterable, Literal

WidgetCategory = Literal["telemetry", "control", "narrative"]
WidgetIntent = Literal["info", "success", "warning", "danger", "neutral"]


@dataclass(slots=True)
class WidgetSpec:
	"""Declarative widget blueprint that can render to markdown or dict."""

	id: str
	title: str
	category: WidgetCategory
	payload: dict[str, Any]
	description: str = ""
	intent: WidgetIntent = "info"
	accent: str = "violet"

	def as_dict(self) -> dict[str, Any]:
		return {
			"id": self.id,
			"title": self.title,
			"category": self.category,
			"payload": self.payload,
			"description": self.description,
			"intent": self.intent,
			"accent": self.accent,
		}

	def render_markdown(self) -> str:
		trend = ""
		if (line := self.payload.get("trend")):
			if isinstance(line, Iterable):
				avg = fmean(line)
				trend = f" · trend avg {avg:.1f}"
		metric = self.payload.get("value")
		return (
			f"### {self.title}\n"
			f"- category: {self.category}\n"
			f"- value: {metric}{trend}\n"
			f"- intent: {self.intent}\n"
			f"{self.description}\n"
		)


@dataclass(slots=True)
class PanelSpec:
	"""Composable arrangement of widgets."""

	id: str
	title: str
	widgets: list[WidgetSpec] = field(default_factory=list)
	purpose: str = ""

	def as_dict(self) -> dict[str, Any]:
		return {
			"id": self.id,
			"title": self.title,
			"purpose": self.purpose,
			"widgets": [widget.as_dict() for widget in self.widgets],
		}

	def render_markdown(self) -> str:
		body = "\n".join(widget.render_markdown() for widget in self.widgets)
		return f"## Panel · {self.title}\n> {self.purpose}\n\n{body}\n"


@dataclass(slots=True)
class PageBlueprint:
	"""Full page layout comprised of multiple panels."""

	slug: str
	title: str
	panels: list[PanelSpec]
	description: str

	def as_dict(self) -> dict[str, Any]:
		return {
			"slug": self.slug,
			"title": self.title,
			"description": self.description,
			"panels": [panel.as_dict() for panel in self.panels],
		}

	def render_markdown(self) -> str:
		content = "\n".join(panel.render_markdown() for panel in self.panels)
		return f"# Page · {self.title}\n_{self.description}_\n\n{content}"


__all__ = [
	"WidgetSpec",
	"PanelSpec",
	"PageBlueprint",
	"WidgetCategory",
	"WidgetIntent",
]
