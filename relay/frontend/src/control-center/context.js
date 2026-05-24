import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { fetchControlStatus, fetchControlWidgets, fetchNotebookJobs, triggerNotebookJob } from "../lib/api";
export const ControlCenterContext = createContext(null);
export function ControlCenterProvider({ children, pollIntervalMs = 5000 }) {
    const [status, setStatus] = useState(null);
    const [widgets, setWidgets] = useState(null);
    const [notebooks, setNotebooks] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState(null);
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
        }
        finally {
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
    const triggerNotebook = useCallback(async (name, parameters) => {
        const job = await triggerNotebookJob({ name, parameters });
        setNotebooks(prev => [job, ...prev.filter(existing => existing.id !== job.id)]);
        return job;
    }, []);
    const value = useMemo(() => ({ status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook }), [status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook]);
    return _jsx(ControlCenterContext.Provider, { value: value, children: children });
}
export function useControlCenter() {
    const context = useContext(ControlCenterContext);
    if (!context) {
        throw new Error("useControlCenter must be used within ControlCenterProvider");
    }
    return context;
}
