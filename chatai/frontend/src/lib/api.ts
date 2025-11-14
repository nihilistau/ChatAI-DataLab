/**
 * Thin fetch helpers for the FastAPI backend with type-safe response mappers.
 */
// @tag: frontend,lib,api

import type {
  ArtifactCreatePayload,
  ArtifactRecord,
  ChatPayload,
  ChatResponsePayload,
  ControlWidgetSnapshot,
  LogTailResponse,
  NotebookJobRecord,
  NotebookRunPayload,
  OpsCommandRequest,
  OpsCommandResponse,
  OpsStatus,
  TailLogEntry,
  TailLogEntryCreate
} from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

const normalizeTimestamp = (value: string | number): number => {
  if (typeof value === "number") return value;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? Date.now() : parsed;
};

const normalizeOptionalTimestamp = (value?: string | number | null): number | undefined => {
  if (value === null || value === undefined) return undefined;
  return normalizeTimestamp(value);
};

const mapArtifactRecord = (input: any): ArtifactRecord => ({
  id: input.id,
  owner: input.owner,
  title: input.title,
  body: input.body,
  accent: input.accent ?? undefined,
  category: input.category,
  updatedAt: normalizeTimestamp(input.updated_at ?? input.updatedAt),
  createdAt: normalizeTimestamp(input.created_at ?? input.createdAt)
});

const mapTailLogEntry = (input: any): TailLogEntry => ({
  id: input.id,
  message: input.message,
  source: input.source,
  createdAt: normalizeTimestamp(input.created_at ?? input.createdAt)
});

export async function postChat(payload: ChatPayload): Promise<ChatResponsePayload> {
  return apiFetch<ChatResponsePayload>(`/api/chat`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function fetchArtifacts(limit = 8): Promise<ArtifactRecord[]> {
  const data = await apiFetch<any[]>(`/api/artifacts?limit=${limit}`);
  return data.map(mapArtifactRecord);
}

export async function createArtifact(payload: ArtifactCreatePayload): Promise<ArtifactRecord> {
  const data = await apiFetch<any>(`/api/artifacts`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return mapArtifactRecord(data);
}

export async function fetchTailLog(limit = 18): Promise<TailLogEntry[]> {
  const data = await apiFetch<any[]>(`/api/tail-log?limit=${limit}`);
  return data.map(mapTailLogEntry);
}

export async function createTailLogEntry(payload: TailLogEntryCreate): Promise<TailLogEntry> {
  const data = await apiFetch<any>(`/api/tail-log`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return mapTailLogEntry(data);
}

export function fetchOpsStatus(): Promise<OpsStatus> {
  return apiFetch<OpsStatus>(`/api/ops/status`);
}

export function sendOpsCommand(payload: OpsCommandRequest): Promise<OpsCommandResponse> {
  return apiFetch<OpsCommandResponse>(`/api/ops/command`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchControlStatus(includeLogs = false, logLines = 60): Promise<OpsStatus> {
  const query = new URLSearchParams({
    include_logs: includeLogs ? "true" : "false",
    log_lines: `${logLines}`
  });
  return apiFetch<OpsStatus>(`/api/control/status?${query.toString()}`);
}

export function fetchControlLogs(service: string, lines = 120): Promise<LogTailResponse> {
  const query = new URLSearchParams({ service, lines: `${lines}` });
  return apiFetch<LogTailResponse>(`/api/control/logs?${query.toString()}`);
}

const mapWidgetSnapshot = (input: any): ControlWidgetSnapshot => ({
  generatedAt: normalizeTimestamp(input.generated_at ?? input.generatedAt ?? Date.now()),
  metrics: (input.metrics ?? []).map((metric: any) => ({
    id: metric.id,
    label: metric.label,
    value: metric.value,
    changePct: metric.change_pct ?? metric.changePct ?? 0,
    unit: metric.unit ?? undefined
  })),
  sparklines: {
    latency: input.sparklines?.latency ?? [],
    ru: input.sparklines?.ru ?? [],
    throughput: input.sparklines?.throughput ?? []
  },
  ruBudget: {
    total: input.ru_budget?.total ?? 0,
    consumed: input.ru_budget?.consumed ?? 0,
    remaining: input.ru_budget?.remaining ?? 0
  }
});

const mapNotebookJob = (input: any): NotebookJobRecord => ({
  id: input.id,
  name: input.name,
  status: input.status,
  createdAt: normalizeTimestamp(input.created_at ?? input.createdAt),
  startedAt: normalizeOptionalTimestamp(input.started_at ?? input.startedAt),
  completedAt: normalizeOptionalTimestamp(input.completed_at ?? input.completedAt),
  outputPath: input.output_path ?? input.outputPath ?? undefined,
  error: input.error ?? undefined,
  parameters: input.parameters ?? {}
});

export async function fetchControlWidgets(): Promise<ControlWidgetSnapshot> {
  const data = await apiFetch<any>(`/api/control/widgets`);
  return mapWidgetSnapshot(data);
}

export async function fetchNotebookJobs(): Promise<NotebookJobRecord[]> {
  const data = await apiFetch<any[]>(`/api/control/notebooks`);
  return data.map(mapNotebookJob);
}

export async function triggerNotebookJob(payload: NotebookRunPayload): Promise<NotebookJobRecord> {
  const data = await apiFetch<any>(`/api/control/notebooks`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return mapNotebookJob(data);
}
