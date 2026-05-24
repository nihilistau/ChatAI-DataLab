import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * Drag-and-drop canvas that tracks hypotheses, shared cards, and assistant
 * insights for the operator workspace.
 */
// @tag: frontend,component,canvas
import { useMemo, useState } from "react";
const sharedColumns = [
    { owner: "shared", title: "Shared Canvas", hint: "Live collaboration" },
    { owner: "assistant", title: "ChatAI Desk", hint: "Autonomous notes" }
];
const ownerOptions = [
    { label: "User", value: "user", helper: "Hypothesis" },
    { label: "Shared", value: "shared", helper: "Signal" },
    { label: "ChatAI", value: "assistant", helper: "Insight" }
];
const categoryOptions = [
    { value: "hypothesis", label: "Hypothesis" },
    { value: "insight", label: "Insight" },
    { value: "signal", label: "Signal" }
];
export default function CanvasBoard({ items, onMove, onCreate, onPromoteToArtifact }) {
    /**
     * Local composer state mirrors the column selections so the UX stays
     * keyboard-friendly without extra context providers.
     */
    const [composerOwner, setComposerOwner] = useState("user");
    const [composerCategory, setComposerCategory] = useState("hypothesis");
    const [title, setTitle] = useState("");
    const [body, setBody] = useState("");
    const grouped = useMemo(() => {
        return items.reduce((acc, item) => {
            acc[item.owner].push(item);
            return acc;
        }, { user: [], shared: [], assistant: [] });
    }, [items]);
    const hypotheses = grouped.user.filter((item) => item.category === "hypothesis");
    const handleDragStart = (event, id) => {
        event.dataTransfer.setData("text/plain", id);
    };
    const handleDrop = (event, owner) => {
        const id = event.dataTransfer.getData("text/plain");
        if (id) {
            onMove(id, owner);
        }
        event.preventDefault();
    };
    const allowDrop = (event) => {
        event.preventDefault();
    };
    const handleSubmit = (event) => {
        event.preventDefault();
        onCreate(composerOwner, title, body, composerCategory);
        setTitle("");
        setBody("");
    };
    return (_jsxs("section", { className: "canvas-board", children: [_jsxs("div", { className: "deck-panel", onDrop: (event) => handleDrop(event, "user"), onDragOver: allowDrop, children: [_jsxs("header", { children: [_jsx("h3", { children: "Hypothesis deck" }), _jsx("p", { children: "Portfolio of the current bets and assumptions." })] }), _jsxs("div", { className: "deck-cards", children: [hypotheses.length === 0 && _jsx("div", { className: "empty-state", children: "Drop a hypothesis to seed the deck" }), hypotheses.map((item) => (_jsxs("article", { className: `deck-card accent-${item.accent ?? "lime"}`, draggable: true, onDragStart: (event) => handleDragStart(event, item.id), children: [_jsxs("div", { className: "card-meta", children: [_jsx("span", { children: new Date(item.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }), _jsx("small", { children: item.category })] }), _jsx("h4", { children: item.title }), _jsx("p", { children: item.body })] }, item.id)))] }), _jsxs("form", { className: "canvas-composer", onSubmit: handleSubmit, children: [_jsx("div", { className: "segmented-control", children: ownerOptions.map((option) => (_jsxs("button", { type: "button", className: composerOwner === option.value ? "segment active" : "segment", onClick: () => {
                                        setComposerOwner(option.value);
                                        if (option.value === "user") {
                                            setComposerCategory("hypothesis");
                                        }
                                        else if (composerCategory === "hypothesis") {
                                            setComposerCategory("insight");
                                        }
                                    }, children: [_jsx("strong", { children: option.label }), _jsx("span", { children: option.helper })] }, option.value))) }), _jsxs("div", { className: "composer-fields", children: [_jsx("select", { value: composerCategory, onChange: (event) => setComposerCategory(event.currentTarget.value), children: categoryOptions.map((option) => (_jsx("option", { value: option.value, children: option.label }, option.value))) }), _jsx("input", { type: "text", placeholder: "Title", value: title, onChange: (event) => setTitle(event.currentTarget.value) }), _jsx("textarea", { placeholder: "Describe the signal, hypothesis, or instruction", value: body, onChange: (event) => setBody(event.currentTarget.value) }), _jsx("div", { className: "composer-actions", children: _jsx("button", { type: "submit", className: "primary", children: "Publish card" }) })] })] })] }), _jsx("div", { className: "board-grid", children: sharedColumns.map((column) => (_jsxs("div", { className: "canvas-column", onDrop: (event) => handleDrop(event, column.owner), onDragOver: allowDrop, children: [_jsxs("header", { children: [_jsx("h3", { children: column.title }), _jsx("p", { children: column.hint })] }), _jsxs("div", { className: "canvas-stack", children: [grouped[column.owner].map((item) => (_jsxs("div", { className: `canvas-card accent-${item.accent ?? "lime"}`, draggable: true, onDragStart: (event) => handleDragStart(event, item.id), children: [_jsxs("div", { className: "card-meta", children: [_jsx("span", { children: new Date(item.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }), _jsx("small", { children: item.category ?? "note" })] }), _jsx("h4", { children: item.title }), _jsx("p", { children: item.body }), _jsx("div", { className: "card-actions", children: _jsx("button", { type: "button", className: "ghost", onClick: () => onPromoteToArtifact(item.id), children: "Artifact" }) })] }, item.id))), grouped[column.owner].length === 0 && _jsx("div", { className: "empty-state", children: "Drop cards here" })] })] }, column.owner))) })] }));
}
