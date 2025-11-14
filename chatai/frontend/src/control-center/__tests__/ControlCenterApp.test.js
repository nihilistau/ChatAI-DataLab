import { jsx as _jsx } from "react/jsx-runtime";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, vi, beforeEach, afterEach, expect } from "vitest";
import ControlCenterApp from "../ControlCenterApp";
const mockFetchControlStatus = vi.fn();
const mockFetchControlWidgets = vi.fn();
const mockFetchNotebookJobs = vi.fn();
const mockTriggerNotebookJob = vi.fn();
const mockSendOpsCommand = vi.fn();
const mockFetchControlLogs = vi.fn();
vi.mock("../../lib/api", () => ({
    fetchControlStatus: (...args) => mockFetchControlStatus(...args),
    fetchControlWidgets: (...args) => mockFetchControlWidgets(...args),
    fetchNotebookJobs: (...args) => mockFetchNotebookJobs(...args),
    triggerNotebookJob: (...args) => mockTriggerNotebookJob(...args),
    sendOpsCommand: (...args) => mockSendOpsCommand(...args),
    fetchControlLogs: (...args) => mockFetchControlLogs(...args)
}));
const statusPayload = {
    services: [
        { name: "backend", state: "running", runtime: "windows", pid: 1234, uptime: 120, display_name: "Backend" }
    ],
    processes: [],
    network: { hostname: "lab", platform: "windows", uptime: 999, bytes_sent: 0, bytes_recv: 0, interfaces: {} },
    logs: {},
    timestamp: Date.now()
};
const widgetsPayload = {
    generatedAt: Date.now(),
    metrics: [
        { id: "latency", label: "LLM Latency", value: 900, changePct: -2.5 },
        { id: "ru-burn", label: "RU Burn", value: 45, changePct: 3.2, unit: "RU/s" },
        { id: "keystrokes", label: "Keystrokes", value: 4000, changePct: 1.1, unit: "events/min" }
    ],
    sparklines: {
        latency: [800, 820, 780, 860],
        ru: [40, 42, 41, 45],
        throughput: [3000, 3100, 3200, 3300]
    },
    ruBudget: { total: 120000, consumed: 40000, remaining: 80000 }
};
const notebooksPayload = [
    {
        id: "job-1",
        name: "control_center_playground.ipynb",
        status: "succeeded",
        createdAt: Date.now() - 5000,
        startedAt: Date.now() - 4000,
        completedAt: Date.now() - 1000,
        parameters: {}
    }
];
const logPayload = { service: "backend", lines: ["Booting", "Ready"] };
beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockFetchControlStatus.mockResolvedValue(statusPayload);
    mockFetchControlWidgets.mockResolvedValue(widgetsPayload);
    mockFetchNotebookJobs.mockResolvedValue(notebooksPayload);
    mockTriggerNotebookJob.mockResolvedValue({ ...notebooksPayload[0], id: "job-2" });
    mockSendOpsCommand.mockResolvedValue({ action: "status", target: "backend", runtime: "auto", output: "ok", timestamp: Date.now() });
    mockFetchControlLogs.mockResolvedValue(logPayload);
});
afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
});
describe("ControlCenterApp", () => {
    it("renders core panels and refreshes data", async () => {
        render(_jsx(ControlCenterApp, {}));
        expect(await screen.findByText(/Service health/i)).toBeInTheDocument();
        expect(screen.getByText(/Notebook monitor/i)).toBeInTheDocument();
        fireEvent.click(screen.getByRole("button", { name: /Refresh/i }));
        await waitFor(() => expect(mockFetchControlStatus).toHaveBeenCalledTimes(2));
    });
    it("triggers notebook runs and tails logs", async () => {
        render(_jsx(ControlCenterApp, {}));
        await screen.findByText(/Notebook monitor/i);
        fireEvent.click(screen.getByRole("button", { name: /Run control_center_playground/i }));
        await waitFor(() => expect(mockTriggerNotebookJob).toHaveBeenCalled());
        vi.advanceTimersByTime(4000);
        await waitFor(() => expect(mockFetchControlLogs).toHaveBeenCalled());
        expect(screen.getByText(/Booting/)).toBeInTheDocument();
    });
});
