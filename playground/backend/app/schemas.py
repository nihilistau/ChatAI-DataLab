from __future__ import annotations

"""Pydantic schemas shared by the FastAPI service."""
# @tag:backend,models

# --- Imports -----------------------------------------------------------------
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt


class APIModel(BaseModel):
    """Shared base model that disables the reserved `model_` namespace."""

    model_config = ConfigDict(protected_namespaces=())


# --- Telemetry payloads ------------------------------------------------------
class KeystrokeEvent(APIModel):
    key: str
    code: Optional[str] = None
    timestamp_ms: PositiveInt = Field(..., description="Milliseconds since epoch")


class PauseEvent(APIModel):
    start_timestamp_ms: PositiveInt
    duration_ms: PositiveInt


class EditSnapshot(APIModel):
    timestamp_ms: PositiveInt
    text: str


class ChatPayload(APIModel):
    final_prompt_text: str = Field(..., min_length=1)
    total_duration_ms: NonNegativeInt
    token_estimate: Optional[NonNegativeInt] = None
    keystroke_events: list[KeystrokeEvent] = Field(default_factory=list)
    pause_events: list[PauseEvent] = Field(default_factory=list)
    edit_history: list[EditSnapshot] = Field(default_factory=list)
    session_id: Optional[str] = None
    ui_version: Optional[str] = None
    model_hint: Optional[str] = None

    def to_metadata_dict(self) -> dict:
        """Flatten nested pydantic models into JSON-ready dictionaries."""

        return {
            "total_duration_ms": self.total_duration_ms,
            "token_estimate": self.token_estimate,
            "keystroke_events": [event.model_dump() for event in self.keystroke_events],
            "pause_events": [event.model_dump() for event in self.pause_events],
            "edit_history": [event.model_dump() for event in self.edit_history],
            "session_id": self.session_id,
            "ui_version": self.ui_version,
            "model_hint": self.model_hint,
        }


class ChatResponse(APIModel):
    interaction_id: UUID
    ai_response_text: str
    model_name: str
    latency_ms: int
    created_at: datetime


class InteractionRead(APIModel):
    id: UUID
    user_prompt_text: str
    typing_metadata_json: dict
    ai_response_text: str
    model_name: str
    latency_ms: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# --- Canvas + artifacts ------------------------------------------------------
CanvasOwner = Literal["user", "shared", "assistant"]
CanvasCategory = Literal["hypothesis", "insight", "signal", "artifact"]


class ArtifactCreate(APIModel):
    title: str = Field(..., max_length=160)
    body: str
    owner: CanvasOwner
    category: CanvasCategory = "artifact"
    accent: Optional[str] = Field(default=None, max_length=16)


class ArtifactRead(ArtifactCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# --- Tail log entries --------------------------------------------------------
class TailLogEntryCreate(APIModel):
    message: str = Field(..., min_length=2)
    source: str = Field(default="system", max_length=48)


class TailLogEntryRead(TailLogEntryCreate):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# --- Ops Deck schemas --------------------------------------------------------
class ServiceStatus(APIModel):
    name: str
    state: str
    runtime: Literal["windows", "linux"]
    display_name: Optional[str] = None
    pid: Optional[int] = None
    uptime: Optional[int] = None
    command: Optional[str] = None
    logPath: Optional[str] = None


class ProcessInfo(APIModel):
    pid: int
    name: Optional[str] = None
    username: Optional[str] = None
    cpu: float
    memory: float
    uptime: int
    cmdline: list[str] = Field(default_factory=list)


class NetworkInterface(APIModel):
    isup: bool = Field(alias="isup")
    speed: Optional[float] = None


class NetworkSnapshot(APIModel):
    hostname: str
    platform: str
    uptime: int
    bytes_sent: int
    bytes_recv: int
    interfaces: dict[str, NetworkInterface]


class OpsStatus(APIModel):
    services: list[ServiceStatus]
    processes: list[ProcessInfo]
    network: NetworkSnapshot
    logs: dict[str, list[str]]
    timestamp: float


OpsAction = Literal["start", "stop", "restart", "status", "logs", "kill", "kill-all"]
OpsRuntime = Literal["auto", "windows", "linux"]


class OpsCommandRequest(APIModel):
    action: OpsAction
    target: Optional[str] = Field(default=None, description="Service name or 'all'")
    runtime: OpsRuntime = "auto"
    log_lines: Optional[int] = Field(default=60, ge=10, le=500)


class OpsCommandResponse(APIModel):
    action: str
    target: str
    runtime: str
    output: str
    timestamp: float


class SearchTelemetryTopPattern(APIModel):
    pattern: str
    runs: int
    total_matches: int
    avg_files_scanned: float


class SearchPresetDrift(APIModel):
    preset: str
    tags: list[str] = Field(default_factory=list)
    total_runs: int
    recent_runs: int
    match_rate_lifetime: float
    match_rate_recent: float
    avg_duration_lifetime: float
    avg_duration_recent: float
    avg_density_lifetime: float
    avg_density_recent: float
    delta_match_rate: float
    delta_duration_ms: float
    delta_density: float
    status: Literal["stable", "regressing", "improving"]


class SearchTelemetrySummary(APIModel):
    total_runs: int
    runs_last_24h: int
    runs_with_matches: int
    match_rate: float
    avg_duration_ms: float | None = None
    avg_match_density: float | None = None
    last_ingest_at: datetime | None = None
    top_patterns: list[SearchTelemetryTopPattern] = Field(default_factory=list)
    preset_drift: list[SearchPresetDrift] = Field(default_factory=list)


# --- Control Center schemas -------------------------------------------------
NotebookStatus = Literal["queued", "running", "succeeded", "failed"]


class LogTailResponse(APIModel):
    service: str
    lines: list[str]


class WidgetMetric(APIModel):
    id: str
    label: str
    value: float
    change_pct: float
    unit: Optional[str] = None


class WidgetSparklines(APIModel):
    latency: list[float]
    ru: list[float]
    throughput: list[float]


class RUBudget(APIModel):
    total: float
    consumed: float
    remaining: float


class ControlWidgetResponse(APIModel):
    generated_at: datetime
    metrics: list[WidgetMetric]
    sparklines: WidgetSparklines
    ru_budget: RUBudget


class NotebookJobRead(APIModel):
    id: str
    name: str
    status: NotebookStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class NotebookRunRequest(APIModel):
    name: str = Field(..., min_length=5, pattern=r".*\.ipynb$")
    parameters: dict[str, Any] = Field(default_factory=dict)


# --- Playground manifest schemas ------------------------------------------
class PlaygroundManifestBase(APIModel):
    cookbook: Optional[str] = Field(default=None, max_length=160)
    recipe: Optional[str] = Field(default=None, max_length=160)
    author: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = None
    revision_label: Optional[str] = Field(default=None, max_length=64)


class PlaygroundManifestCreate(PlaygroundManifestBase):
    manifest: dict[str, Any]
    revision: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional explicit revision number. Leave blank to auto-increment.",
    )


class PlaygroundManifestRead(PlaygroundManifestBase):
    id: str
    tenant: str
    playground: str
    revision: int
    manifest: dict[str, Any]
    checksum: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# --- Elements schemas -------------------------------------------------------
class GraphEdgeEndpoint(APIModel):
    node: str
    port: str


class GraphEdge(APIModel):
    id: str
    source: GraphEdgeEndpoint = Field(..., alias="from")
    target: GraphEdgeEndpoint = Field(..., alias="to")

    model_config = ConfigDict(populate_by_name=True)


class GraphNode(APIModel):
    id: str
    type: str
    label: str
    props: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] = Field(default_factory=dict)


class GraphMetadata(APIModel):
    tags: list[str] | None = None
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    updated_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class GraphPayload(APIModel):
    name: str
    tenant_id: str = Field(..., alias="tenantId")
    workspace_id: str = Field(..., alias="workspaceId")
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metadata: Optional[GraphMetadata] = None

    model_config = ConfigDict(populate_by_name=True)


class GraphCreateRequest(GraphPayload):
    pass


class GraphUpdateRequest(GraphPayload):
    pass


class GraphRead(GraphPayload):
    id: str
    created_at: datetime
    updated_at: datetime


class NodeOverride(APIModel):
    props: dict[str, Any] = Field(default_factory=dict)


class GraphRunRequest(APIModel):
    overrides: dict[str, NodeOverride] = Field(
        default_factory=dict,
        description="Optional map of nodeId -> property overrides applied just for this run",
    )


GraphRunStatus = Literal["queued", "running", "succeeded", "failed"]


class GraphNodeTrace(APIModel):
    id: str
    type: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    props: dict[str, Any]


class GraphRunRead(APIModel):
    id: str
    graph_id: str
    status: GraphRunStatus
    created_at: datetime
    completed_at: datetime | None = None
    outputs: dict[str, Any]
    trace: list[GraphNodeTrace]
    error: Optional[str] = None


# --- Command tracker schemas -----------------------------------------------
CommandStatus = Literal["never-run", "running", "succeeded", "failed"]


class CommandExecutionRead(APIModel):
    timestamp: datetime
    status: CommandStatus
    exit_code: Optional[int] = None
    output: Optional[str] = None
    notes: Optional[str] = None
    failed: bool
    command: Optional[str] = None


class CommandRecord(APIModel):
    id: str
    label: str
    command: str
    created_at: datetime
    added_by: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    working_dir: Optional[str] = None
    last_status: CommandStatus
    last_run_at: Optional[datetime] = None
    history: list[CommandExecutionRead] = Field(default_factory=list)


class CommandCreateRequest(APIModel):
    label: str = Field(..., min_length=2)
    command: str = Field(..., min_length=2)
    tags: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    added_by: Optional[str] = None
    working_dir: Optional[str] = None


class CommandRunRequest(APIModel):
    dry_run: bool = False
    shell: Optional[str] = None
