import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import "../elements.css";
export const Surface = ({ title, description, children }) => (_jsxs("section", { className: "elements-surface", children: [title && (_jsxs("header", { style: { marginBottom: "0.75rem" }, children: [_jsx("p", { style: { margin: 0, fontSize: "0.85rem", color: "#7dd3fc" }, children: title }), description && (_jsx("span", { style: { color: "#cbd5f5", fontSize: "0.85rem" }, children: description }))] })), children] }));
export const Stack = ({ gap = "1rem", direction = "column", className, children }) => (_jsx("div", { className: `elements-stack ${className ?? ""}`.trim(), style: { gap, flexDirection: direction }, children: children }));
export const MetricCard = ({ label, value, hint }) => (_jsxs("div", { style: {
        borderRadius: "12px",
        border: "1px solid rgba(148, 163, 184, 0.3)",
        padding: "0.75rem 1rem",
        background: "rgba(8, 47, 73, 0.5)",
        display: "flex",
        flexDirection: "column",
        gap: "0.25rem"
    }, children: [_jsx("span", { style: { fontSize: "0.85rem", textTransform: "uppercase", color: "#bae6fd" }, children: label }), _jsx("strong", { style: { fontSize: "1.5rem", lineHeight: 1 }, children: value }), hint && _jsx("span", { style: { color: "#94a3b8", fontSize: "0.8rem" }, children: hint })] }));
