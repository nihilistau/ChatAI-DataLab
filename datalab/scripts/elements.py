"""DataLab helpers for working with Elements graphs inside notebooks."""
# @tag: datalab,scripts,elements

from __future__ import annotations

from collections import Counter, defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

GraphDict = dict[str, Any]

_SAMPLE_GRAPHS: dict[str, GraphDict] = {
    "qa_loop": {
        "name": "LLM QA Loop",
        "tenantId": "lab",
        "workspaceId": "default",
        "nodes": [
            {"id": "node_prompt", "type": "prompt", "label": "Prompt", "props": {"text": "Hello"}},
            {
                "id": "node_llm",
                "type": "llm",
                "label": "LLM",
                "props": {"model": "gpt-4o-mini", "temperature": 0.1},
            },
            {
                "id": "node_notebook",
                "type": "notebook",
                "label": "Notebook",
                "props": {"notebook": "control_center_playground.ipynb"},
            },
        ],
        "edges": [
            {
                "id": "edge_prompt_llm",
                "from": {"node": "node_prompt", "port": "text"},
                "to": {"node": "node_llm", "port": "prompt"},
            },
            {
                "id": "edge_llm_notebook",
                "from": {"node": "node_llm", "port": "response"},
                "to": {"node": "node_notebook", "port": "parameters"},
            },
        ],
        "metadata": {"tags": ["qa"], "createdBy": "notebook"},
    },
    "insight_report": {
        "name": "Insight Report",
        "tenantId": "lab",
        "workspaceId": "default",
        "nodes": [
            {
                "id": "node_report_prompt",
                "type": "prompt",
                "label": "Report Prompt",
                "props": {"text": "Summarize the latest lab findings"},
            },
            {
                "id": "node_report_llm",
                "type": "llm",
                "label": "Summary LLM",
                "props": {"model": "gpt-4o-mini", "temperature": 0.2},
            },
            {
                "id": "node_report_notebook",
                "type": "notebook",
                "label": "Notebook Export",
                "props": {
                    "notebook": "elements_reporting.ipynb",
                    "parameters": {"format": "markdown"},
                },
            },
        ],
        "edges": [
            {
                "id": "edge_prompt_llm",
                "from": {"node": "node_report_prompt", "port": "text"},
                "to": {"node": "node_report_llm", "port": "prompt"},
            },
            {
                "id": "edge_llm_notebook",
                "from": {"node": "node_report_llm", "port": "response"},
                "to": {"node": "node_report_notebook", "port": "parameters"},
            },
        ],
        "metadata": {"tags": ["report"], "createdBy": "notebook"},
    },
}


@dataclass
class ExecutionTraceEntry:
    """Record of one node execution step."""

    id: str
    type: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    props: dict[str, Any]


def load_graph(graph_source: str | Path | GraphDict | None = None, *, preset: str = "qa_loop") -> GraphDict:
    """Return a graph dict drawn from disk, a preset name, or an existing mapping."""

    if graph_source is None:
        return deepcopy(_SAMPLE_GRAPHS[preset])

    if isinstance(graph_source, (str, Path)):
        path = Path(graph_source)
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    return deepcopy(graph_source)


def available_presets() -> list[str]:
    return sorted(_SAMPLE_GRAPHS.keys())


def graph_summary(graph: GraphDict) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    type_counts = Counter(node.get("type", "unknown") for node in nodes)
    return {
        "name": graph.get("name", "Unnamed"),
        "tenantId": graph.get("tenantId"),
        "workspaceId": graph.get("workspaceId"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(type_counts),
        "tags": graph.get("metadata", {}).get("tags", []),
    }


def build_execution_plan(graph: GraphDict) -> list[dict[str, Any]]:
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    incoming = _incoming_edges(graph)
    order = _topological_order(nodes.keys(), graph.get("edges", []))
    plan = []
    for step_index, node_id in enumerate(order, start=1):
        node = nodes[node_id]
        deps = [edge["from"]["node"] for edge in incoming.get(node_id, [])]
        plan.append(
            {
                "step": step_index,
                "node": node_id,
                "type": node.get("type", "unknown"),
                "depends_on": deps,
            }
        )
    return plan


def simulate_graph(graph: GraphDict, overrides: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    nodes = {node["id"]: deepcopy(node) for node in graph.get("nodes", [])}
    if not nodes:
        raise ValueError("Graph requires at least one node")

    overrides = overrides or {}
    incoming = _incoming_edges(graph)
    order = _topological_order(nodes.keys(), graph.get("edges", []))
    context: dict[str, dict[str, Any]] = {}
    trace: list[ExecutionTraceEntry] = []

    for node_id in order:
        node = nodes[node_id]
        handler = _get_handler(node.get("type", ""))
        if handler is None:
            raise ValueError(f"Unsupported node type: {node.get('type')}")
        props = {**node.get("props", {}), **overrides.get(node_id, {})}
        inputs = _gather_inputs(node_id, incoming, context)
        outputs = handler(node, props, inputs)
        context[node_id] = outputs
        trace.append(ExecutionTraceEntry(id=node_id, type=node.get("type", ""), inputs=inputs, outputs=outputs, props=props))

    final_outputs = context[order[-1]]
    return {
        "status": "succeeded",
        "outputs": final_outputs,
        "trace": [entry.__dict__ for entry in trace],
    }


def export_trace(trace: Iterable[dict[str, Any]] | Iterable[ExecutionTraceEntry], destination: Path) -> Path:
    payload = [entry.__dict__ if isinstance(entry, ExecutionTraceEntry) else entry for entry in trace]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def write_graph(graph: GraphDict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return destination


def _incoming_edges(graph: GraphDict) -> dict[str, list[dict[str, Any]]]:
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.get("edges", []):
        target = _edge_endpoint(edge, "to").get("node")
        if not target:
            continue
        incoming[target].append(edge)
    return incoming


def _topological_order(node_ids: Iterable[str], edges: list[dict[str, Any]]) -> list[str]:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}

    for edge in edges:
        source = _edge_endpoint(edge, "from").get("node")
        target = _edge_endpoint(edge, "to").get("node")
        if not source or not target:
            continue
        adjacency[source].append(target)
        indegree[target] += 1

    queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    order: list[str] = []

    while queue:
        current = queue.popleft()
        order.append(current)
        for neighbor in adjacency[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(adjacency):
        raise ValueError("Graph contains a cycle")
    return order


def _gather_inputs(node_id: str, incoming: dict[str, list[dict[str, Any]]], context: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ports: dict[str, Any] = {}
    for edge in incoming.get(node_id, []):
        from_ep = _edge_endpoint(edge, "from")
        to_ep = _edge_endpoint(edge, "to")
        source_node = from_ep.get("node")
        source_port = from_ep.get("port")
        target_port = to_ep.get("port")
        source_outputs = context.get(source_node, {})
        if source_node and target_port:
            ports[target_port] = source_outputs.get(source_port)
    return ports


def _get_handler(node_type: str):
    return {
        "prompt": _handle_prompt,
        "llm": _handle_llm,
        "notebook": _handle_notebook,
    }.get(node_type)


def _edge_endpoint(edge: dict[str, Any], direction: str) -> dict[str, Any]:
    if direction == "from":
        return edge.get("from") or edge.get("source", {}) or {}
    if direction == "to":
        return edge.get("to") or edge.get("target", {}) or {}
    return {}


def _handle_prompt(_: dict[str, Any], props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    text = props.get("text") or inputs.get("text") or ""
    variant = props.get("variant", "raw")
    return {"text": str(text), "variant": variant}


def _handle_llm(_: dict[str, Any], props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    prompt_value = inputs.get("prompt") or inputs.get("text") or props.get("prompt") or ""
    model = props.get("model", "gpt-4o-mini")
    temperature = props.get("temperature", 0.2)
    response = f"[{model} | temp={temperature}] {prompt_value}".strip()
    return {"response": response, "model": model, "temperature": temperature}


def _handle_notebook(_: dict[str, Any], props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    notebook = props.get("notebook", "control_center_playground.ipynb")
    parameters = {**props.get("parameters", {}), "inputs": inputs}
    return {"status": "queued", "notebook": notebook, "parameters": parameters}
