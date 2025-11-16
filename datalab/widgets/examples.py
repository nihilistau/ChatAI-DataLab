from __future__ import annotations

"""Sample widget collections for notebooks + CLI demos."""

from dataclasses import dataclass
from typing import Iterable

from .base import PageBlueprint, PanelSpec, WidgetSpec


def telemetry_widgets() -> list[WidgetSpec]:
    return [
        WidgetSpec(
            id="latency",
            title="Latency Orbit",
            category="telemetry",
            payload={"value": "118 ms", "trend": [90, 82, 75, 70, 65, 60]},
            description="p95 ms for inference pods",
            intent="info",
            accent="plasma",
        ),
        WidgetSpec(
            id="ru-budget",
            title="RU Budget",
            category="telemetry",
            payload={"value": "72%", "trend": [60, 64, 66, 70, 72]},
            description="Guardrail for Cosmos consumption",
            intent="warning",
            accent="lime",
        ),
        WidgetSpec(
            id="guardrails",
            title="Guardrail Health",
            category="telemetry",
            payload={"value": "86% pass", "trend": [70, 75, 80, 82, 86]},
            description="Live pass rate",
            intent="success",
            accent="forest",
        ),
        WidgetSpec(
            id="tokens",
            title="Token Drift",
            category="telemetry",
            payload={"value": "1.3k avg", "trend": [32, 45, 60, 58, 72, 80]},
            description="Rolling token consumption for prompts",
            intent="info",
            accent="violet",
        ),
        WidgetSpec(
            id="alerts",
            title="Anomaly Alerts",
            category="telemetry",
            payload={"value": "7 active", "trend": [1, 2, 3, 4, 7]},
            description="Unacknowledged anomalies across tenants",
            intent="danger",
            accent="ember",
        ),
    ]


def control_widgets() -> list[WidgetSpec]:
    return [
        WidgetSpec(
            id="command-deck",
            title="Command Deck",
            category="control",
            payload={"value": "restart api"},
            description="Primary macro used by ops lead",
            intent="danger",
            accent="peach",
        ),
        WidgetSpec(
            id="scale-notebooks",
            title="Notebook Scale",
            category="control",
            payload={"value": "scale notebooks"},
            description="Auto-scaling macro",
            intent="success",
            accent="forest",
        ),
        WidgetSpec(
            id="sync-telemetry",
            title="Sync Telemetry",
            category="control",
            payload={"value": "sync telemetry"},
            description="Refreshes search + ops deck",
            intent="info",
            accent="plasma",
        ),
        WidgetSpec(
            id="guardrail-audit",
            title="Guardrail Audit",
            category="control",
            payload={"value": "launch audit"},
            description="Runs compliance notebook",
            intent="warning",
            accent="ember",
        ),
        WidgetSpec(
            id="theme-switch",
            title="Theme Switch",
            category="control",
            payload={"value": "apply neon"},
            description="UI theming hook",
            intent="info",
            accent="cobalt",
        ),
    ]


def narrative_widgets() -> list[WidgetSpec]:
    return [
        WidgetSpec(
            id="insight",
            title="Prompt Rhythm Insight",
            category="narrative",
            payload={"value": "+18% quality"},
            description="Cadence vs quality story",
            intent="success",
            accent="peach",
        ),
        WidgetSpec(
            id="persona",
            title="Ops Persona",
            category="narrative",
            payload={"value": "ops lead"},
            description="Role-specific needs",
            intent="info",
            accent="forest",
        ),
        WidgetSpec(
            id="win-log",
            title="Win Log",
            category="narrative",
            payload={"value": "3 wins"},
            description="Recent achievements",
            intent="success",
            accent="lime",
        ),
        WidgetSpec(
            id="design-tenets",
            title="Design Tenets",
            category="narrative",
            payload={"value": "3 pillars"},
            description="Guiding design rules",
            intent="info",
            accent="violet",
        ),
        WidgetSpec(
            id="signal-story",
            title="Signal Story",
            category="narrative",
            payload={"value": "guardrail adoption"},
            description="Narrative snippet for leadership",
            intent="warning",
            accent="ember",
        ),
    ]


def showcase_panels() -> list[PanelSpec]:
    telem = telemetry_widgets()
    control = control_widgets()
    narr = narrative_widgets()
    groups = [
        PanelSpec(
            id="ops-flight",
            title="Ops Flight",
            purpose="Mix telemetry + macros",
            widgets=[telem[0], control[0], telem[2]],
        ),
        PanelSpec(
            id="notebook-flight",
            title="Notebook Flight",
            purpose="Notebook success + control",
            widgets=[telem[1], control[1], narr[0]],
        ),
        PanelSpec(
            id="signal-canvas",
            title="Signal Canvas",
            purpose="Narratives with live data",
            widgets=[narr[2], telem[3]],
        ),
        PanelSpec(
            id="guardrail",
            title="Guardrail Sentinel",
            purpose="Audit-friendly view",
            widgets=[telem[2], control[3], telem[4]],
        ),
        PanelSpec(
            id="insight-anthology",
            title="Insight Anthology",
            purpose="Story-driven console",
            widgets=[narr[0], narr[3], control[2]],
        ),
    ]
    return groups


def blueprint_pages() -> list[PageBlueprint]:
    panels = showcase_panels()
    return [
        PageBlueprint(
            slug="ops-garden",
            title="Ops Garden",
            description="Cluster awareness page blending latency, guardrails, and macros.",
            panels=[panels[0], panels[3]],
        ),
        PageBlueprint(
            slug="notebook-studio",
            title="Notebook Studio",
            description="Design-forward run studio for power users.",
            panels=[panels[1], panels[4]],
        ),
        PageBlueprint(
            slug="signal-weather",
            title="Signal Weather",
            description="Executive-ready story mixing telemetry and narratives.",
            panels=[panels[2], panels[4]],
        ),
    ]


@dataclass(slots=True)
class WidgetLibrary:
    """Convenience container exposing both widgets + panels."""

    telemetry: list[WidgetSpec]
    control: list[WidgetSpec]
    narrative: list[WidgetSpec]
    panels: list[PanelSpec]
    pages: list[PageBlueprint]

    def category(self, name: str) -> list[WidgetSpec]:
        collection = getattr(self, name, None)
        if collection is None:
            raise KeyError(name)
        return collection

    def to_markdown(self) -> str:
        sections = []
        for label, widgets in (
            ("Telemetry", self.telemetry),
            ("Control", self.control),
            ("Narrative", self.narrative),
        ):
            widget_blob = "\n".join(widget.render_markdown() for widget in widgets)
            sections.append(f"# {label} widgets\n{widget_blob}")
        panel_blob = "\n".join(panel.render_markdown() for panel in self.panels)
        page_blob = "\n".join(page.render_markdown() for page in self.pages)
        sections.append(f"# Panels\n{panel_blob}")
        sections.append(f"# Pages\n{page_blob}")
        return "\n\n".join(sections)


def build_library() -> WidgetLibrary:
    return WidgetLibrary(
        telemetry=telemetry_widgets(),
        control=control_widgets(),
        narrative=narrative_widgets(),
        panels=showcase_panels(),
        pages=blueprint_pages(),
    )
