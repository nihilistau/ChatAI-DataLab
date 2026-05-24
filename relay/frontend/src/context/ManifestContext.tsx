import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { RelayManifestRecord } from "../types";
import { fetchLatestRelayManifest } from "../lib/api";

export const DEFAULT_RELAY_TENANT = import.meta.env.VITE_RELAY_TENANT ?? "demo-tenant";
export const DEFAULT_RELAY_NAME = import.meta.env.VITE_RELAY_NAME ?? "welcome-control";

const AUTO_REFRESH_STORAGE_KEY = "chatai.manifest.autoRefresh";

export interface ManifestContextValue {
  tenant: string;
  relay: string;
  manifest: RelayManifestRecord | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  status: string | null;
  lastFetched: number | null;
  refresh: () => Promise<void>;
  pollIntervalMs: number;
  autoRefreshEnabled: boolean;
  setAutoRefreshEnabled: (enabled: boolean) => void;
}

export const ManifestContext = createContext<ManifestContextValue | null>(null);

interface ManifestProviderProps {
  children: React.ReactNode;
  tenant?: string;
  relay?: string;
  pollIntervalMs?: number;
}

export function ManifestProvider({
  children,
  tenant = DEFAULT_RELAY_TENANT,
  relay = DEFAULT_RELAY_NAME,
  pollIntervalMs = 60000
}: ManifestProviderProps) {
  const [manifest, setManifest] = useState<RelayManifestRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<number | null>(null);
  const [autoRefreshEnabled, setAutoRefreshEnabledState] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    const stored = window.localStorage.getItem(AUTO_REFRESH_STORAGE_KEY);
    return stored === "true";
  });

  const setAutoRefreshEnabled = useCallback((enabled: boolean) => {
    setAutoRefreshEnabledState(enabled);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(AUTO_REFRESH_STORAGE_KEY, autoRefreshEnabled ? "true" : "false");
  }, [autoRefreshEnabled]);

  const applyManifestPayload = useCallback(
    (payload: RelayManifestRecord | null) => {
      if (payload) {
        setManifest(payload);
        setStatus(null);
        setError(null);
      } else {
        setManifest(null);
        setStatus(`No manifest published for ${tenant}/${relay} yet. Run the Welcome Cookbook to push one.`);
        setError(null);
      }
      setLastFetched(Date.now());
    },
    [relay, tenant]
  );

  const fetchManifestRecord = useCallback(async () => {
    return fetchLatestRelayManifest(tenant, relay);
  }, [tenant, relay]);

  const runFetch = useCallback(async () => {
    try {
      const latest = await fetchManifestRecord();
      applyManifestPayload(latest);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load manifest";
      setError(message);
    }
  }, [applyManifestPayload, fetchManifestRecord]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await runFetch();
    setRefreshing(false);
    setLoading(false);
  }, [runFetch]);

  useEffect(() => {
    let cancelled = false;
    const initialize = async () => {
      setLoading(true);
      try {
        const latest = await fetchManifestRecord();
        if (cancelled) return;
        applyManifestPayload(latest);
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to load manifest";
        setError(message);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    };

    void initialize();
    return () => {
      cancelled = true;
    };
  }, [applyManifestPayload, fetchManifestRecord]);

  useEffect(() => {
    if (!autoRefreshEnabled) return;
    const id = window.setInterval(() => {
      void refresh();
    }, pollIntervalMs);
    return () => {
      window.clearInterval(id);
    };
  }, [autoRefreshEnabled, pollIntervalMs, refresh]);

  const value = useMemo<ManifestContextValue>(
    () => ({
      tenant,
      relay,
      manifest,
      loading,
      refreshing,
      error,
      status,
      lastFetched,
      refresh,
      pollIntervalMs,
      autoRefreshEnabled,
      setAutoRefreshEnabled
    }),
    [autoRefreshEnabled, error, lastFetched, loading, manifest, relay, pollIntervalMs, refresh, refreshing, setAutoRefreshEnabled, status, tenant]
  );

  return <ManifestContext.Provider value={value}>{children}</ManifestContext.Provider>;
}

export function useManifest(): ManifestContextValue {
  const context = useContext(ManifestContext);
  if (!context) {
    throw new Error("useManifest must be used within a ManifestProvider");
  }
  return context;
}
