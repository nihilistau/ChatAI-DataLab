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
