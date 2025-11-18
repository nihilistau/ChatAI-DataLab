from __future__ import annotations

"""Execution helpers for the Elements node graph preview."""

# @tag:backend,services,elements

from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from ..schemas import (
    GraphNode,
    GraphEdge,
    GraphPayload,
    GraphRunStatus,
)


class GraphValidationError(ValueError):
    """Raised when a graph definition is invalid or cannot be executed."""


@dataclass
class GraphExecutionResult:
    status: GraphRunStatus
    outputs: dict[str, Any]
    trace: list[dict[str, Any]]
    error: str | None = None


NodeHandler = Callable[[GraphNode, dict[str, Any], dict[str, Any]], dict[str, Any]]


class GraphExecutor:
    """Perform deterministic execution of graph nodes using built-in handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {
            "prompt": self._handle_prompt,
            "llm": self._handle_llm,
            "notebook": self._handle_notebook,
        }

    def execute(
        self,
        graph: GraphPayload,
        overrides: dict[str, dict[str, Any]] | None = None,
    ) -> GraphExecutionResult:
        if not graph.nodes:
            raise GraphValidationError("Graph must contain at least one node")

        overrides = overrides or {}
        nodes_by_id = {node.id: node for node in graph.nodes}
        self._validate_edges(graph.edges, nodes_by_id)

        incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
        indegree: dict[str, int] = {node_id: 0 for node_id in nodes_by_id}

        for edge in graph.edges:
            incoming[edge.target.node].append(edge)
            adjacency[edge.source.node].append(edge.target.node)
            indegree[edge.target.node] += 1

        order = self._topological_order(indegree, adjacency)
        context: dict[str, dict[str, Any]] = {}
        trace: list[dict[str, Any]] = []

        for node_id in order:
            node = nodes_by_id[node_id]
            handler = self._handlers.get(node.type)
            if handler is None:
                raise GraphValidationError(f"No executor available for node type '{node.type}'")

            props = {**node.props, **overrides.get(node_id, {})}
            inputs = self._gather_inputs(node_id, incoming, context)
            outputs = handler(node, props, inputs)
            context[node_id] = outputs
            trace.append(
                {
                    "id": node.id,
                    "type": node.type,
                    "inputs": inputs,
                    "outputs": outputs,
                    "props": props,
                }
            )

        final_outputs = context[order[-1]] if order else {}
        return GraphExecutionResult(status="succeeded", outputs=final_outputs, trace=trace)

    @staticmethod
    def _validate_edges(edges: list[GraphEdge], nodes: dict[str, GraphNode]) -> None:
        for edge in edges:
            if edge.source.node not in nodes:
                raise GraphValidationError(f"Edge references unknown source node '{edge.source.node}'")
            if edge.target.node not in nodes:
                raise GraphValidationError(f"Edge references unknown target node '{edge.target.node}'")

    @staticmethod
    def _topological_order(indegree: dict[str, int], adjacency: dict[str, list[str]]) -> list[str]:
        queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adjacency[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(indegree):
            raise GraphValidationError("Graph contains a cycle; execution aborted")
        return order

    @staticmethod
    def _gather_inputs(
        node_id: str,
        incoming: dict[str, list[GraphEdge]],
        context: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        ports: dict[str, Any] = {}
        for edge in incoming.get(node_id, []):
            source_outputs = context.get(edge.source.node, {})
            ports[edge.target.port] = source_outputs.get(edge.source.port)
        return ports

    @staticmethod
    def _handle_prompt(_: GraphNode, props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        text = props.get("text") or inputs.get("text") or props.get("title") or ""
        variant = props.get("variant", "raw")
        return {
            "text": str(text),
            "variant": variant,
        }

    @staticmethod
    def _handle_llm(_: GraphNode, props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        prompt_value = inputs.get("prompt") or inputs.get("text") or props.get("prompt") or ""
        model = props.get("model", "gpt-4o-mini")
        temperature = props.get("temperature", 0.2)
        response = f"[{model} | temp={temperature}] {prompt_value}".strip()
        return {
            "response": response,
            "model": model,
            "temperature": temperature,
        }

    @staticmethod
    def _handle_notebook(_: GraphNode, props: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        notebook = props.get("notebook", "control_center_playground.ipynb")
        parameters = {
            **props.get("parameters", {}),
            "inputs": inputs,
        }
        return {
            "status": "queued",
            "notebook": notebook,
            "parameters": parameters,
        }


_GRAPH_EXECUTOR: GraphExecutor | None = None


def get_graph_executor() -> GraphExecutor:
    global _GRAPH_EXECUTOR
    if _GRAPH_EXECUTOR is None:
        _GRAPH_EXECUTOR = GraphExecutor()
    return _GRAPH_EXECUTOR


def set_graph_executor(executor: GraphExecutor | None) -> None:
    global _GRAPH_EXECUTOR
    _GRAPH_EXECUTOR = executor
