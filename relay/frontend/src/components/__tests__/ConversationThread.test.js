import { jsx as _jsx } from "react/jsx-runtime";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConversationThread from "../ConversationThread";
describe("ConversationThread", () => {
    const baseMessages = [
        {
            id: "1",
            role: "system",
            content: "System ready",
            timestamp: new Date("2024-01-01T12:00:00Z").getTime()
        },
        {
            id: "2",
            role: "user",
            content: "Hello",
            timestamp: new Date("2024-01-01T12:00:01Z").getTime(),
            tokenEstimate: 4
        },
        {
            id: "3",
            role: "assistant",
            content: "Hi there",
            timestamp: new Date("2024-01-01T12:00:02Z").getTime()
        }
    ];
    it("renders each message with friendly role labels", () => {
        render(_jsx(ConversationThread, { messages: baseMessages }));
        expect(screen.getByText("System")).toBeInTheDocument();
        expect(screen.getByText("You")).toBeInTheDocument();
        expect(screen.getByText("ChatAI")).toBeInTheDocument();
    });
    it("shows token estimates when provided", () => {
        render(_jsx(ConversationThread, { messages: baseMessages }));
        expect(screen.getByText(/4 tokens est./i)).toBeInTheDocument();
    });
});
