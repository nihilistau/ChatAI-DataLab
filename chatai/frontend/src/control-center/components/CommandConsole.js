import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { sendOpsCommand } from "../../lib/api";
const ACTIONS = ["status", "start", "stop", "restart", "logs"];
export const CommandConsole = () => {
    const [action, setAction] = useState("status");
    const [target, setTarget] = useState("backend");
    const [output, setOutput] = useState("Ready.");
    const [isRunning, setIsRunning] = useState(false);
    const handleRun = async () => {
        setIsRunning(true);
        try {
            const response = await sendOpsCommand({ action, target });
            setOutput(response.output || JSON.stringify(response, null, 2));
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            setOutput(message);
        }
        finally {
            setIsRunning(false);
        }
    };
    return (_jsxs("section", { className: "control-card command-console", children: [_jsx("header", { className: "control-card__header", children: _jsxs("div", { children: [_jsx("h2", { children: "Command console" }), _jsx("p", { children: "Send Ops Deck commands via the FastAPI relay." })] }) }), _jsxs("div", { className: "command-console__form", children: [_jsxs("label", { children: ["Action", _jsx("select", { value: action, onChange: event => setAction(event.target.value), children: ACTIONS.map(option => (_jsx("option", { value: option, children: option }, option))) })] }), _jsxs("label", { children: ["Target", _jsx("select", { value: target, onChange: event => setTarget(event.target.value), children: ['backend', 'frontend', 'datalab', 'all'].map(name => (_jsx("option", { value: name, children: name }, name))) })] }), _jsx("button", { onClick: handleRun, disabled: isRunning, children: isRunning ? "Running…" : "Execute" })] }), _jsx("pre", { className: "command-console__output", "aria-live": "polite", children: output })] }));
};
