/**
 * Read-only transcript stack that streams prompt/response pairs with basic
 * role styling.
 */
// @tag: frontend,component,conversation

import type { ConversationMessage } from "../types";

interface ConversationThreadProps {
  messages: ConversationMessage[];
}

const roleLabels: Record<ConversationMessage["role"], string> = {
  system: "System",
  user: "You",
  assistant: "ChatAI"
};

export default function ConversationThread({ messages }: ConversationThreadProps) {
  return (
    <div className="conversation-thread" aria-live="polite">
      {messages.map((message) => (
        <article key={message.id} className={`message message-${message.role}`}>
          <header>
            <span className="role">{roleLabels[message.role]}</span>
            <span className="timestamp">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </header>
          <p>{message.content}</p>
          {message.tokenEstimate && (
            <footer>
              <small>{message.tokenEstimate} tokens est.</small>
            </footer>
          )}
        </article>
      ))}
    </div>
  );
}
