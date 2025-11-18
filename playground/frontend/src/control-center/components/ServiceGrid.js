import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const formatUptime = (uptime) => {
    if (!uptime)
        return "n/a";
    const minutes = Math.floor(uptime / 60);
    if (minutes < 60)
        return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
};
export const ServiceGrid = ({ status }) => {
    if (!status) {
        return _jsx("div", { className: "control-card control-card--muted", children: "Waiting for orchestrator snapshot\u2026" });
    }
    return (_jsxs("section", { className: "control-card", children: [_jsx("header", { className: "control-card__header", children: _jsxs("div", { children: [_jsx("h2", { children: "Service health" }), _jsx("p", { children: "Aggregated view from Lab Orchestrator" })] }) }), _jsx("div", { className: "service-grid", children: status.services.map(service => (_jsxs("article", { className: "service-tile", children: [_jsx("div", { className: `service-status ${service.state}`, children: service.state }), _jsx("h3", { children: service.display_name ?? service.name }), _jsxs("dl", { children: [_jsxs("div", { children: [_jsx("dt", { children: "Runtime" }), _jsx("dd", { children: service.runtime })] }), _jsxs("div", { children: [_jsx("dt", { children: "Uptime" }), _jsx("dd", { children: formatUptime(service.uptime) })] }), _jsxs("div", { children: [_jsx("dt", { children: "PID" }), _jsx("dd", { children: service.pid ?? "n/a" })] })] })] }, service.name))) })] }));
};
