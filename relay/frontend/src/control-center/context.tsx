import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ControlWidgetSnapshot, NotebookJobRecord, OpsStatus } from "../types";
import { fetchControlStatus, fetchControlWidgets, fetchNotebookJobs, triggerNotebookJob } from "../lib/api";

interface ControlCenterContextValue {
  status: OpsStatus | null;
  widgets: ControlWidgetSnapshot | null;
  notebooks: NotebookJobRecord[];
  lastUpdated: number | null;
  isRefreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  triggerNotebook: (name: string, parameters?: Record<string, unknown>) => Promise<NotebookJobRecord>;
}

export const ControlCenterContext = createContext<ControlCenterContextValue | null>(null);

interface ProviderProps {
  children: React.ReactNode;
  pollIntervalMs?: number;
}

export function ControlCenterProvider({ children, pollIntervalMs = 5000 }: ProviderProps) {
  const [status, setStatus] = useState<OpsStatus | null>(null);
  const [widgets, setWidgets] = useState<ControlWidgetSnapshot | null>(null);
  const [notebooks, setNotebooks] = useState<NotebookJobRecord[]>([]);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [statusPayload, widgetPayload, notebookPayload] = await Promise.all([
        fetchControlStatus(false),
        fetchControlWidgets(),
        fetchNotebookJobs()
      ]);
      setStatus(statusPayload);
      setWidgets(widgetPayload);
      setNotebooks(notebookPayload);
      setLastUpdated(Date.now());
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      void refresh();
    }, pollIntervalMs);
    return () => window.clearInterval(id);
  }, [pollIntervalMs, refresh]);

  const triggerNotebook = useCallback(
    async (name: string, parameters?: Record<string, unknown>) => {
      const job = await triggerNotebookJob({ name, parameters });
      setNotebooks(prev => [job, ...prev.filter(existing => existing.id !== job.id)]);
      return job;
    },
    []
  );

  const value = useMemo<ControlCenterContextValue>(
    () => ({ status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook }),
    [status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook]
  );

  return <ControlCenterContext.Provider value={value}>{children}</ControlCenterContext.Provider>;
}

export function useControlCenter(): ControlCenterContextValue {
  const context = useContext(ControlCenterContext);
  if (!context) {
    throw new Error("useControlCenter must be used within ControlCenterProvider");
  }
  return context;
}
