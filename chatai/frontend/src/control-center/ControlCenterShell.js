import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useControlCenter } from "./context";
import { MetricsPanel } from "./components/MetricsPanel";
import { ServiceGrid } from "./components/ServiceGrid";
import { NotebookMonitor } from "./components/NotebookMonitor";
import { CommandConsole } from "./components/CommandConsole";
import { TailLogViewer } from "./components/TailLogViewer";
import "./styles.css";
const formatUpdated = (timestamp) => (timestamp ? new Date(timestamp).toLocaleTimeString() : "—");
export const ControlCenterShell = () => {
    const { status, widgets, notebooks, lastUpdated, isRefreshing, error, refresh, triggerNotebook } = useControlCenter();
    const handleNotebookRun = (parameters) => triggerNotebook("control_center_playground.ipynb", parameters);
    return (_jsxs("main", { className: "control-center-shell", children: [_jsxs("header", { className: "control-header", children: [_jsxs("div", { children: [_jsx("p", { children: "Control Center" }), _jsx("h1", { children: "Playground automation + Ops telemetry" })] }), _jsxs("div", { className: "header-actions", children: [_jsxs("span", { children: ["Last updated: ", formatUpdated(lastUpdated)] }), _jsx("button", { onClick: () => refresh(), disabled: isRefreshing, children: isRefreshing ? "Refreshing…" : "Refresh" })] })] }), error && _jsx("div", { className: "control-banner control-banner--error", children: error }), _jsx(MetricsPanel, { widgets: widgets }), _jsxs("div", { className: "control-grid control-grid--two-column", children: [_jsx(ServiceGrid, { status: status }), _jsx(NotebookMonitor, { notebooks: notebooks, onRun: handleNotebookRun })] }), _jsxs("div", { className: "control-grid control-grid--two-column", children: [_jsx(CommandConsole, {}), _jsx(TailLogViewer, {})] })] }));
};
