import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * Mirror of the backend tail log that keeps a copyable buffer in the UI.
 */
// @tag: frontend,component,telemetry
import { useMemo, useState } from "react";
const formatEntry = (entry) => {
    const time = new Date(entry.createdAt).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
    return `${time} ${entry.source} · ${entry.message}`;
};
export default function TailLogCell({ entries }) {
    const [copied, setCopied] = useState(false);
    const logBlob = useMemo(() => entries.map(formatEntry).join("\n"), [entries]);
    const handleCopy = async () => {
        if (!navigator?.clipboard) {
            return;
        }
        try {
            await navigator.clipboard.writeText(logBlob || "log idle");
            setCopied(true);
            setTimeout(() => setCopied(false), 1800);
        }
        catch (error) {
            console.warn("Clipboard copy failed", error);
        }
    };
    return (_jsxs("section", { className: "tail-log-panel", children: [_jsxs("header", { className: "panel-header", children: [_jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Tails feed" }), _jsx("h3", { children: "Selectable log output" })] }), _jsx("button", { type: "button", className: "ghost", onClick: handleCopy, children: copied ? "Copied" : "Copy" })] }), _jsxs("div", { className: "tail-log-scroll", children: [entries.length === 0 && _jsx("div", { className: "empty-state", children: "Tail log idle" }), entries.map((entry) => (_jsxs("article", { className: "tail-log-entry", children: [_jsxs("header", { children: [_jsx("span", { children: new Date(entry.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) }), _jsx("small", { children: entry.source })] }), _jsx("p", { children: entry.message })] }, entry.id)))] })] }));
}
