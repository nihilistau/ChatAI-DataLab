import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
const formatTimestamp = (timestamp) => {
    if (!timestamp)
        return "pending";
    return new Date(timestamp).toLocaleTimeString();
};
export const NotebookMonitor = ({ notebooks, onRun }) => {
    const [dbPath, setDbPath] = useState("./interactions.db");
    const [statusUrl, setStatusUrl] = useState("http://localhost:8000/api/control/status");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [feedback, setFeedback] = useState(null);
    const handleRun = async () => {
        setIsSubmitting(true);
        setFeedback(null);
        try {
            await onRun({ DB_PATH: dbPath, CONTROL_STATUS_URL: statusUrl, OUTPUT_DIR: "./_papermill" });
            setFeedback("Notebook run triggered");
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setFeedback(message);
        }
        finally {
            setIsSubmitting(false);
        }
    };
    return (_jsxs("section", { className: "control-card notebook-monitor", children: [_jsx("header", { className: "control-card__header", children: _jsxs("div", { children: [_jsx("h2", { children: "Notebook monitor" }), _jsx("p", { children: "Trigger Papermill runs and inspect the latest executions." })] }) }), _jsxs("div", { className: "notebook-form", children: [_jsxs("label", { children: ["DB Path", _jsx("input", { value: dbPath, onChange: event => setDbPath(event.target.value) })] }), _jsxs("label", { children: ["Control Status URL", _jsx("input", { value: statusUrl, onChange: event => setStatusUrl(event.target.value) })] }), _jsx("button", { onClick: handleRun, disabled: isSubmitting, children: isSubmitting ? "Triggering…" : "Run control_center_playground.ipynb" }), feedback && _jsx("p", { className: "notebook-feedback", children: feedback })] }), _jsxs("ul", { className: "notebook-list", children: [notebooks.map(job => (_jsxs("li", { children: [_jsxs("div", { children: [_jsx("strong", { children: job.name }), _jsx("span", { children: job.status.toUpperCase() })] }), _jsxs("p", { children: ["Started: ", formatTimestamp(job.startedAt), " \u00B7 Completed: ", formatTimestamp(job.completedAt)] })] }, job.id))), !notebooks.length && _jsx("li", { children: "No notebook executions recorded yet." })] })] }));
};
