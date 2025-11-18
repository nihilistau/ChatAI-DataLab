import { GraphDefinition } from "./types";

export const defaultGraph: GraphDefinition = {
  id: "graph_default",
  name: "LLM QA Loop",
  tenantId: "lab",
  workspaceId: "default",
  nodes: [
    {
      id: "node_prompt",
      type: "prompt",
      label: "Prompt",
      props: { title: "User prompt" },
      position: { x: 150, y: 50 }
    },
    {
      id: "node_llm",
      type: "llm",
      label: "LLM",
      props: { model: "gpt-4o-mini", temperature: 0.2 },
      position: { x: 420, y: 200 }
    },
    {
      id: "node_notebook",
      type: "notebook",
      label: "Notebook",
      props: { notebook: "control_center_playground.ipynb" },
      position: { x: 700, y: 360 }
    }
  ],
  edges: [
    { id: "edge_prompt_llm", from: { node: "node_prompt", port: "text" }, to: { node: "node_llm", port: "prompt" } },
    { id: "edge_llm_notebook", from: { node: "node_llm", port: "response" }, to: { node: "node_notebook", port: "parameters" } }
  ],
  metadata: {
    tags: ["qa", "demo"],
    createdBy: "nihil"
  }
};
