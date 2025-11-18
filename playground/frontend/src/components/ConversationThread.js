import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const roleLabels = {
    system: "System",
    user: "You",
    assistant: "ChatAI"
};
export default function ConversationThread({ messages }) {
    return (_jsx("div", { className: "conversation-thread", "aria-live": "polite", children: messages.map((message) => (_jsxs("article", { className: `message message-${message.role}`, children: [_jsxs("header", { children: [_jsx("span", { className: "role", children: roleLabels[message.role] }), _jsx("span", { className: "timestamp", children: new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) })] }), _jsx("p", { children: message.content }), message.tokenEstimate && (_jsx("footer", { children: _jsxs("small", { children: [message.tokenEstimate, " tokens est."] }) }))] }, message.id))) }));
}
