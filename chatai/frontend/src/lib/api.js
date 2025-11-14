/**
 * Thin fetch helpers for the FastAPI backend with type-safe response mappers.
 */
// @tag: frontend,lib,api
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
async function apiFetch(path, init) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
        ...init
    });
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Request failed (${response.status}): ${detail || response.statusText}`);
    }
    return response.json();
}
const normalizeTimestamp = (value) => {
    if (typeof value === "number")
        return value;
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? Date.now() : parsed;
};
const normalizeOptionalTimestamp = (value) => {
    if (value === null || value === undefined)
        return undefined;
    return normalizeTimestamp(value);
};
const mapArtifactRecord = (input) => ({
    id: input.id,
    owner: input.owner,
    title: input.title,
    body: input.body,
    accent: input.accent ?? undefined,
    category: input.category,
    updatedAt: normalizeTimestamp(input.updated_at ?? input.updatedAt),
    createdAt: normalizeTimestamp(input.created_at ?? input.createdAt)
});
const mapTailLogEntry = (input) => ({
    id: input.id,
    message: input.message,
    source: input.source,
    createdAt: normalizeTimestamp(input.created_at ?? input.createdAt)
});
export async function postChat(payload) {
    return apiFetch(`/api/chat`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
}
export async function fetchArtifacts(limit = 8) {
    const data = await apiFetch(`/api/artifacts?limit=${limit}`);
    return data.map(mapArtifactRecord);
}
export async function createArtifact(payload) {
    const data = await apiFetch(`/api/artifacts`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
    return mapArtifactRecord(data);
}
export async function fetchTailLog(limit = 18) {
    const data = await apiFetch(`/api/tail-log?limit=${limit}`);
    return data.map(mapTailLogEntry);
}
export async function createTailLogEntry(payload) {
    const data = await apiFetch(`/api/tail-log`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
    return mapTailLogEntry(data);
}
export function fetchOpsStatus() {
    return apiFetch(`/api/ops/status`);
}
export function sendOpsCommand(payload) {
    return apiFetch(`/api/ops/command`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
}
export function fetchControlStatus(includeLogs = false, logLines = 60) {
    const query = new URLSearchParams({
        include_logs: includeLogs ? "true" : "false",
        log_lines: `${logLines}`
    });
    return apiFetch(`/api/control/status?${query.toString()}`);
}
export function fetchControlLogs(service, lines = 120) {
    const query = new URLSearchParams({ service, lines: `${lines}` });
    return apiFetch(`/api/control/logs?${query.toString()}`);
}
const mapWidgetSnapshot = (input) => ({
    generatedAt: normalizeTimestamp(input.generated_at ?? input.generatedAt ?? Date.now()),
    metrics: (input.metrics ?? []).map((metric) => ({
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
const mapNotebookJob = (input) => ({
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
export async function fetchControlWidgets() {
    const data = await apiFetch(`/api/control/widgets`);
    return mapWidgetSnapshot(data);
}
export async function fetchNotebookJobs() {
    const data = await apiFetch(`/api/control/notebooks`);
    return data.map(mapNotebookJob);
}
export async function triggerNotebookJob(payload) {
    const data = await apiFetch(`/api/control/notebooks`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
    return mapNotebookJob(data);
}
