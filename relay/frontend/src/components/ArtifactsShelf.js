import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function ArtifactsShelf({ artifacts, onSelect }) {
    /**
     * Render the shelf inline when artifacts exist; otherwise stay hidden to
     * reduce chrome.
     */
    if (!artifacts.length) {
        return null;
    }
    return (_jsxs("section", { className: "artifacts-shelf", children: [_jsx("header", { className: "panel-header", children: _jsxs("div", { children: [_jsx("p", { className: "eyebrow", children: "Artifacts rail" }), _jsx("h2", { children: "Persistent evidence locker" })] }) }), _jsx("div", { className: "artifact-rail", children: artifacts.map((artifact) => (_jsxs("article", { className: `artifact-card accent-${artifact.accent ?? "violet"}`, children: [_jsxs("div", { className: "artifact-headline", children: [_jsx("h3", { children: artifact.title }), _jsx("span", { children: new Date(artifact.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) })] }), _jsx("p", { children: artifact.body }), onSelect && (_jsx("div", { className: "artifact-actions", children: _jsx("button", { type: "button", className: "ghost", onClick: () => onSelect(artifact), children: "Insert" }) }))] }, artifact.id))) })] }));
}
