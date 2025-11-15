export const builtInNodes = [
    {
        type: "prompt",
        version: "1.0.0",
        label: "Prompt",
        icon: "🗒️",
        summary: "Collects or transforms user prompts",
        inputs: {
            text: { key: "text", label: "Prompt text", accepts: ["text"], direction: "in", required: false }
        },
        outputs: {
            text: { key: "text", label: "Prompt", accepts: ["text"], direction: "out", required: true }
        },
        propsSchema: {
            title: { type: "string", default: "New prompt" },
            variant: { type: "string", enum: ["raw", "template"] }
        },
        runtime: { executor: "client", handler: "prompt.execute" }
    },
    {
        type: "llm",
        version: "1.0.0",
        label: "LLM Call",
        icon: "⚡",
        summary: "Calls a configured large language model",
        inputs: {
            prompt: { key: "prompt", label: "Prompt", accepts: ["text"], direction: "in", required: true },
            context: { key: "context", label: "Context", accepts: ["json", "vector"], direction: "in", required: false }
        },
        outputs: {
            response: { key: "response", label: "Response", accepts: ["text"], direction: "out", required: true }
        },
        propsSchema: {
            model: { type: "string", enum: ["gpt-4o-mini", "gpt-4o", "claude-3-sonnet"], default: "gpt-4o-mini" },
            temperature: { type: "number", minimum: 0, maximum: 2, default: 0.2 },
            maxTokens: { type: "number", minimum: 64, maximum: 4096, default: 1024 }
        },
        runtime: { executor: "server", handler: "llm.invoke" }
    },
    {
        type: "notebook",
        version: "1.0.0",
        label: "Notebook",
        icon: "📓",
        summary: "Triggers a parameterized Papermill run",
        inputs: {
            parameters: { key: "parameters", label: "Parameters", accepts: ["json"], direction: "in", required: false }
        },
        outputs: {
            artifact: { key: "artifact", label: "Artifact", accepts: ["file", "json"], direction: "out", required: false },
            status: { key: "status", label: "Run status", accepts: ["json"], direction: "out", required: true }
        },
        propsSchema: {
            notebook: { type: "string", default: "control_center_playground.ipynb" },
            kernel: { type: "string", default: "python3" }
        },
        runtime: { executor: "server", handler: "notebooks.run" }
    }
];
