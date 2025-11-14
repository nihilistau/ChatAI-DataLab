import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { fetchControlLogs } from "../../lib/api";
const SERVICES = ["backend", "frontend", "datalab", "playground"];
export const TailLogViewer = () => {
    const [service, setService] = useState(SERVICES[0]);
    const [lines, setLines] = useState([]);
    const [error, setError] = useState(null);
    useEffect(() => {
        let active = true;
        const load = async () => {
            try {
                const response = await fetchControlLogs(service, 120);
                if (active) {
                    setLines(response.lines);
                    setError(null);
                }
            }
            catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                if (active) {
                    setError(message);
                }
            }
        };
        void load();
        const id = window.setInterval(() => {
            void load();
        }, 4000);
        return () => {
            active = false;
            window.clearInterval(id);
        };
    }, [service]);
    return (_jsxs("section", { className: "control-card tail-log-viewer", children: [_jsxs("header", { className: "control-card__header", children: [_jsxs("div", { children: [_jsx("h2", { children: "Tail logs" }), _jsxs("p", { children: ["Streaming from ", _jsx("code", { children: `.labctl/logs/${service}.log` }), "."] })] }), _jsx("select", { value: service, onChange: event => setService(event.target.value), children: SERVICES.map(name => (_jsx("option", { value: name, children: name }, name))) })] }), error && _jsx("p", { className: "error-text", children: error }), _jsx("pre", { className: "log-output", "aria-live": "polite", children: lines.length ? lines.join("\n") : "No log lines yet." })] }));
};
