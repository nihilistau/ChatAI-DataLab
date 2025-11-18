/** Shared UI contracts mirroring backend schemas for strict typing. */
// @tag: frontend,types,contracts

export interface KeystrokeEvent {
  key: string;
  code: string;
  timestamp_ms: number;
}

export interface PauseEvent {
  start_timestamp_ms: number;
  duration_ms: number;
}

export interface EditSnapshot {
  timestamp_ms: number;
  text: string;
}

export interface ChatPayload {
  final_prompt_text: string;
  total_duration_ms: number;
  token_estimate?: number;
  keystroke_events: KeystrokeEvent[];
  pause_events: PauseEvent[];
  edit_history: EditSnapshot[];
  session_id?: string;
  ui_version?: string;
  model_hint?: string;
}

export type ConversationRole = "system" | "user" | "assistant";

export interface ConversationMessage {
  id: string;
  role: ConversationRole;
  content: string;
  timestamp: number;
  tokenEstimate?: number;
}

export type CanvasOwner = "user" | "shared" | "assistant";

export type CanvasCategory = "hypothesis" | "insight" | "artifact" | "signal";

export interface CanvasItem {
  id: string;
  owner: CanvasOwner;
  title: string;
  body: string;
  accent?: "lime" | "forest" | "peach" | "violet";
  updatedAt: number;
  category?: CanvasCategory;
}

export interface ArtifactRecord extends CanvasItem {
  createdAt: number;
}

export interface ArtifactCreatePayload {
  title: string;
  body: string;
  owner: CanvasOwner;
  category?: CanvasCategory;
  accent?: CanvasItem["accent"];
}

export interface TailLogEntry {
  id: string;
  message: string;
  source: string;
  createdAt: number;
}

export interface TailLogEntryCreate {
  message: string;
  source?: string;
}

export interface ChatResponsePayload {
  interaction_id: string;
  ai_response_text: string;
  model_name?: string;
}

export type OpsAction = "start" | "stop" | "restart" | "status" | "logs" | "kill" | "kill-all";

export interface ServiceStatus {
  name: string;
  state: string;
  runtime: "windows" | "linux";
  display_name?: string;
  pid?: number;
  uptime?: number;
  command?: string;
  logPath?: string;
}

export interface ProcessInfo {
  pid: number;
  name?: string;
  username?: string;
  cpu: number;
  memory: number;
  uptime: number;
  cmdline: string[];
}

export interface NetworkInterfaceInfo {
  isup: boolean;
  speed?: number;
}

export interface NetworkSnapshot {
  hostname: string;
  platform: string;
  uptime: number;
  bytes_sent: number;
  bytes_recv: number;
  interfaces: Record<string, NetworkInterfaceInfo>;
}

export interface OpsStatus {
  services: ServiceStatus[];
  processes: ProcessInfo[];
  network: NetworkSnapshot;
  logs: Record<string, string[]>;
  timestamp: number;
}

export interface OpsCommandRequest {
  action: OpsAction;
  target?: string;
  runtime?: "auto" | "windows" | "linux";
  log_lines?: number;
}

export interface OpsCommandResponse {
  action: OpsAction;
  target: string;
  runtime: string;
  output: string;
  timestamp: number;
}

export interface LogTailResponse {
  service: string;
  lines: string[];
}

export type NotebookStatus = "queued" | "running" | "succeeded" | "failed";

export interface NotebookJobRecord {
  id: string;
  name: string;
  status: NotebookStatus;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  outputPath?: string;
  error?: string;
  parameters: Record<string, unknown>;
}

export interface NotebookRunPayload {
  name: string;
  parameters?: Record<string, unknown>;
}

export interface WidgetMetric {
  id: string;
  label: string;
  value: number;
  changePct: number;
  unit?: string;
}

export interface WidgetSparklines {
  latency: number[];
  ru: number[];
  throughput: number[];
}

export interface RUBudget {
  total: number;
  consumed: number;
  remaining: number;
}

export interface ControlWidgetSnapshot {
  generatedAt: number;
  metrics: WidgetMetric[];
  sparklines: WidgetSparklines;
  ruBudget: RUBudget;
}

export interface SearchTelemetryTopPattern {
  pattern: string;
  runs: number;
  totalMatches: number;
  avgFilesScanned: number;
}

export type PresetDriftStatus = "stable" | "regressing" | "improving";

export interface SearchPresetDrift {
  preset: string;
  tags: string[];
  totalRuns: number;
  recentRuns: number;
  matchRateLifetime: number;
  matchRateRecent: number;
  avgDurationLifetime: number;
  avgDurationRecent: number;
  avgDensityLifetime: number;
  avgDensityRecent: number;
  deltaMatchRate: number;
  deltaDurationMs: number;
  deltaDensity: number;
  status: PresetDriftStatus;
}

export interface SearchTelemetrySummary {
  totalRuns: number;
  runsLast24h: number;
  runsWithMatches: number;
  matchRate: number;
  avgDurationMs?: number | null;
  avgMatchDensity?: number | null;
  lastIngestAt?: number | null;
  topPatterns: SearchTelemetryTopPattern[];
  presetDrift: SearchPresetDrift[];
}

// --- Playground manifest contracts ---------------------------------------

export type PlaygroundActionMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | string;

export interface PlaygroundAction {
  id?: string;
  title?: string;
  route: string;
  method?: PlaygroundActionMethod;
  description?: string;
}

export interface PlaygroundWidget {
  id?: string;
  type: string;
  title?: string;
  props?: Record<string, unknown>;
}

export interface PlaygroundLayoutSection {
  id?: string;
  title?: string;
  description?: string;
  accent?: string;
  span?: "full" | "half" | "third";
  widgets?: PlaygroundWidget[];
}

export interface PlaygroundLayout {
  sections?: PlaygroundLayoutSection[];
}

export interface PlaygroundManifest {
  version?: number;
  layout?: PlaygroundLayout;
  actions?: PlaygroundAction[];
  metadata?: Record<string, unknown>;
}

export interface PlaygroundManifestRecord {
  id: string;
  tenant: string;
  playground: string;
  revision: number;
  revisionLabel?: string;
  cookbook?: string;
  recipe?: string;
  author?: string;
  notes?: string;
  manifest: PlaygroundManifest;
  checksum: string;
  createdAt: number;
  updatedAt: number;
}
