/**
 * Thin fetch helpers for the FastAPI backend with type-safe response mappers.
 */
// @tag: frontend,lib,api
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const CONTROL_STATUS_FIXTURE = import.meta.env.VITE_CONTROL_STATUS_FIXTURE;
async function apiRequest(path, init) {
    return fetch(`${API_BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
        ...init
    });
}
async function apiFetch(path, init) {
    const response = await apiRequest(path, init);
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Request failed (${response.status}): ${detail || response.statusText}`);
    }
    return response.json();
}
async function apiFetchNullable(path, init) {
    const response = await apiRequest(path, init);
    if (response.status === 404) {
        return null;
    }
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Request failed (${response.status}): ${detail || response.statusText}`);
    }
    if (response.status === 204) {
        return null;
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
const mapPlaygroundManifestRecord = (input) => ({
    id: input.id,
    tenant: input.tenant,
    playground: input.playground,
    revision: input.revision,
    revisionLabel: input.revision_label ?? input.revisionLabel ?? undefined,
    cookbook: input.cookbook ?? undefined,
    recipe: input.recipe ?? undefined,
    author: input.author ?? undefined,
    notes: input.notes ?? undefined,
    manifest: input.manifest ?? {},
    checksum: input.checksum,
    createdAt: normalizeTimestamp(input.created_at ?? input.createdAt),
    updatedAt: normalizeTimestamp(input.updated_at ?? input.updatedAt)
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
export async function fetchControlStatus(includeLogs = false, logLines = 60) {
    if (CONTROL_STATUS_FIXTURE) {
        const response = await fetch(CONTROL_STATUS_FIXTURE, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Fixture fetch failed (${response.status}): ${response.statusText}`);
        }
        return response.json();
    }
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
const mapTelemetrySummary = (input) => ({
    totalRuns: input.total_runs ?? input.totalRuns ?? 0,
    runsLast24h: input.runs_last_24h ?? input.runsLast24h ?? 0,
    runsWithMatches: input.runs_with_matches ?? input.runsWithMatches ?? 0,
    matchRate: input.match_rate ?? input.matchRate ?? 0,
    avgDurationMs: input.avg_duration_ms ?? input.avgDurationMs ?? null,
    avgMatchDensity: input.avg_match_density ?? input.avgMatchDensity ?? null,
    lastIngestAt: normalizeOptionalTimestamp(input.last_ingest_at ?? input.lastIngestAt),
    topPatterns: (input.top_patterns ?? input.topPatterns ?? []).map((pattern) => ({
        pattern: pattern.pattern,
        runs: pattern.runs,
        totalMatches: pattern.total_matches ?? pattern.totalMatches ?? 0,
        avgFilesScanned: pattern.avg_files_scanned ?? pattern.avgFilesScanned ?? 0
    })),
    presetDrift: (input.preset_drift ?? input.presetDrift ?? []).map((entry) => ({
        preset: entry.preset,
        tags: entry.tags ?? [],
        totalRuns: entry.total_runs ?? entry.totalRuns ?? 0,
        recentRuns: entry.recent_runs ?? entry.recentRuns ?? 0,
        matchRateLifetime: entry.match_rate_lifetime ?? entry.matchRateLifetime ?? 0,
        matchRateRecent: entry.match_rate_recent ?? entry.matchRateRecent ?? 0,
        avgDurationLifetime: entry.avg_duration_lifetime ?? entry.avgDurationLifetime ?? 0,
        avgDurationRecent: entry.avg_duration_recent ?? entry.avgDurationRecent ?? 0,
        avgDensityLifetime: entry.avg_density_lifetime ?? entry.avgDensityLifetime ?? 0,
        avgDensityRecent: entry.avg_density_recent ?? entry.avgDensityRecent ?? 0,
        deltaMatchRate: entry.delta_match_rate ?? entry.deltaMatchRate ?? 0,
        deltaDurationMs: entry.delta_duration_ms ?? entry.deltaDurationMs ?? 0,
        deltaDensity: entry.delta_density ?? entry.deltaDensity ?? 0,
        status: entry.status ?? "stable"
    }))
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
export async function fetchSearchTelemetrySummary() {
    const data = await apiFetch(`/api/ops/search-telemetry`);
    return mapTelemetrySummary(data);
}
export async function fetchLatestPlaygroundManifest(tenant, playground) {
    const data = await apiFetchNullable(`/api/playgrounds/${tenant}/${playground}/manifests/latest`);
    return data ? mapPlaygroundManifestRecord(data) : null;
}
