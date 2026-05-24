import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const formatValue = (value, unit) => {
    const rounded = Math.round(value * 100) / 100;
    return unit ? `${rounded.toLocaleString()} ${unit}` : rounded.toLocaleString();
};
const Sparkline = ({ points }) => {
    if (!points.length)
        return null;
    const maxValue = Math.max(...points);
    return (_jsx("div", { className: "control-sparkline", "aria-label": "trend sparkline", children: points.map((point, idx) => {
            const height = maxValue === 0 ? 0 : (point / maxValue) * 100;
            return _jsx("span", { style: { height: `${height || 2}%` } }, `spark-${idx}`);
        }) }));
};
export const MetricsPanel = ({ widgets }) => {
    if (!widgets) {
        return _jsx("div", { className: "control-card control-card--muted", children: "Loading metrics\u2026" });
    }
    return (_jsxs("section", { className: "control-metrics", "aria-live": "polite", children: [widgets.metrics.map(metric => (_jsxs("article", { className: "control-card", children: [_jsxs("header", { children: [_jsx("span", { className: "metric-label", children: metric.label }), _jsxs("span", { className: `metric-change ${metric.changePct >= 0 ? "positive" : "negative"}`, children: [metric.changePct >= 0 ? "▲" : "▼", " ", Math.abs(metric.changePct).toFixed(2), "%"] })] }), _jsx("div", { className: "metric-value", children: formatValue(metric.value, metric.unit) }), _jsx(Sparkline, { points: widgets.sparklines[metric.id === "ru-burn" ? "ru" : metric.id === "keystrokes" ? "throughput" : "latency"] ?? [] })] }, metric.id))), _jsxs("article", { className: "control-card", children: [_jsx("header", { children: _jsx("span", { className: "metric-label", children: "RU Budget" }) }), _jsxs("div", { className: "ru-budget", children: [_jsx("div", { className: "ru-budget__bar", children: _jsx("div", { className: "ru-budget__bar-fill", style: { width: `${(widgets.ruBudget.consumed / widgets.ruBudget.total) * 100}%` } }) }), _jsxs("p", { children: [widgets.ruBudget.remaining.toLocaleString(), " RU remaining"] })] })] })] }));
};
