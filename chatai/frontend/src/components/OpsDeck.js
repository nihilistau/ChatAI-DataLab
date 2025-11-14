import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * Control panel for orchestrating backend/frontend/datalab services plus
 * viewing logs, processes, and network stats.
 */
// @tag: frontend,component,ops
import { useMemo, useState } from "react";
const SERVICE_ORDER = ["backend", "frontend", "datalab"];
const WORKFLOWS = [
    {
        title: "Full stack reboot",
        steps: ["Stop all services", "Flush caches", "Restart orchestration"],
        actions: ["stop", "kill-all", "start"]
    },
    {
        title: "Frontend refresh",
        steps: ["Restart Vite dev server", "Open telemetry stream"],
        actions: ["restart", "logs"],
        target: "frontend"
    },
    {
        title: "DataLab warm-up",
        steps: ["Start notebooks", "Tail lab logs"],
        actions: ["start", "logs"],
        target: "datalab"
    }
];
function formatSeconds(seconds) {
    if (!seconds || seconds < 0)
        return "—";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) {
        return `${hrs}h ${mins}m`;
    }
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
}
const OpsDeck = ({ status, onCommand, busyAction = null }) => {
    const [selectedService, setSelectedService] = useState(SERVICE_ORDER[0]);
    const serviceSnapshot = useMemo(() => {
        if (!status)
            return undefined;
        const direct = status.services.find((svc) => svc.name === selectedService);
        if (direct)
            return direct;
        return status.services[0];
    }, [status, selectedService]);
    const logLines = serviceSnapshot ? status?.logs?.[serviceSnapshot.name] ?? [] : [];
    const processes = status?.processes ?? [];
    const network = status?.network;
    const handleAction = async (action, target) => {
        await onCommand(action, target ?? serviceSnapshot?.name);
    };
    return (_jsxs("section", { className: "ops-deck", children: [_jsxs("header", { className: "panel-header", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Operations" }), _jsx("h2", { children: "Control center" })] }), _jsx("div", { className: "ops-service-selector", children: SERVICE_ORDER.map((service) => (_jsx("button", { className: service === (serviceSnapshot?.name ?? selectedService) ? "chip active" : "chip", onClick: () => setSelectedService(service), children: service }, service))) })] }), _jsxs("div", { className: "ops-grid", children: [_jsxs("div", { className: "ops-glass", children: [_jsxs("div", { className: "ops-service-meta", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Service" }), _jsx("h3", { children: serviceSnapshot?.display_name ?? serviceSnapshot?.name ?? "—" })] }), _jsx("div", { className: `status-pill ${serviceSnapshot?.state?.toLowerCase() ?? "idle"}`, children: serviceSnapshot?.state ?? "idle" })] }), _jsxs("div", { className: "ops-actions", children: [_jsx("button", { onClick: () => handleAction("start"), disabled: busyAction === "start", children: "Start" }), _jsx("button", { onClick: () => handleAction("restart"), disabled: busyAction === "restart", children: "Restart" }), _jsx("button", { onClick: () => handleAction("stop"), disabled: busyAction === "stop", children: "Stop" }), _jsx("button", { className: "danger", onClick: () => handleAction("kill"), disabled: busyAction === "kill", children: "Kill" })] }), _jsxs("dl", { className: "ops-meta", children: [_jsxs("div", { children: [_jsx("dt", { children: "Runtime" }), _jsx("dd", { children: serviceSnapshot?.runtime ?? "—" })] }), _jsxs("div", { children: [_jsx("dt", { children: "PID" }), _jsx("dd", { children: serviceSnapshot?.pid ?? "—" })] }), _jsxs("div", { children: [_jsx("dt", { children: "Uptime" }), _jsx("dd", { children: formatSeconds(serviceSnapshot?.uptime) })] })] })] }), _jsxs("div", { className: "ops-terminal", children: [_jsxs("header", { children: [_jsxs("span", { children: ["log \u00B7 ", serviceSnapshot?.name ?? "—"] }), _jsx("div", { className: "terminal-actions", children: _jsx("button", { onClick: () => handleAction("logs"), disabled: busyAction === "logs", children: "Refresh" }) })] }), _jsx("pre", { children: (logLines.length ? logLines : ["No log entries yet."]).map((line) => (_jsx("span", { children: line }, line + Math.random()))) })] })] }), _jsxs("div", { className: "ops-lower", children: [_jsxs("div", { className: "process-panel", children: [_jsxs("div", { className: "panel-subheader", children: [_jsx("p", { className: "eyebrow", children: "Processes" }), _jsx("button", { onClick: () => handleAction("status"), disabled: busyAction === "status", children: "Snapshot" })] }), _jsxs("div", { className: "process-table", children: [_jsxs("div", { className: "process-row head", children: [_jsx("span", { children: "PID" }), _jsx("span", { children: "Name" }), _jsx("span", { children: "CPU" }), _jsx("span", { children: "Memory" }), _jsx("span", { children: "Uptime" })] }), processes.map((proc) => (_jsxs("div", { className: "process-row", children: [_jsx("span", { children: proc.pid }), _jsx("span", { children: proc.name ?? "—" }), _jsxs("span", { children: [proc.cpu.toFixed(1), "%"] }), _jsxs("span", { children: [proc.memory.toFixed(1), "%"] }), _jsx("span", { children: formatSeconds(proc.uptime) })] }, proc.pid)))] })] }), _jsxs("div", { className: "network-panel", children: [_jsx("p", { className: "eyebrow", children: "Network" }), _jsx("h3", { children: network?.hostname ?? "—" }), _jsxs("ul", { children: [_jsxs("li", { children: ["Platform \u00B7 ", network?.platform ?? "unknown"] }), _jsxs("li", { children: ["Uptime \u00B7 ", formatSeconds(network?.uptime)] }), _jsxs("li", { children: ["Sent \u00B7 ", network ? (network.bytes_sent / 1000000).toFixed(1) : "0", " MB"] }), _jsxs("li", { children: ["Recv \u00B7 ", network ? (network.bytes_recv / 1000000).toFixed(1) : "0", " MB"] })] })] }), _jsxs("div", { className: "workflow-panel", children: [_jsx("p", { className: "eyebrow", children: "Workflows" }), _jsx("div", { className: "workflow-grid", children: WORKFLOWS.map((flow) => (_jsxs("article", { children: [_jsxs("header", { children: [_jsx("h4", { children: flow.title }), _jsxs("small", { children: [flow.steps.length, " steps"] })] }), _jsx("ol", { children: flow.steps.map((step) => (_jsx("li", { children: step }, step))) }), _jsx("div", { className: "workflow-actions", children: flow.actions.map((action) => (_jsx("button", { onClick: () => handleAction(action, flow.target), disabled: busyAction === action, children: action }, `${flow.title}-${action}`))) })] }, flow.title))) })] })] })] }));
};
export default OpsDeck;
