# Copyright 2026 TRACE contributors
"""Standard LangGraph Server entrypoints; the server owns checkpoint storage."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .config import Settings
from .evidence import Evidence, MCPEvidence
from .model import OpenAIReasoner, Reasoner
from .nodes import Nodes
from .state import InputState, State
from .tools import build_tools


def build_graph(
    evidence: Evidence,
    model: Reasoner | None = None,
    checkpointer: BaseCheckpointSaver[str] | None = None,
) -> CompiledStateGraph[State, None, InputState, State]:
    """Compile a single ReAct loop with deterministic lifecycle nodes."""
    tools = build_tools(evidence)
    nodes = Nodes(evidence, model or OpenAIReasoner(Settings(), tools))
    builder = StateGraph(State, input_schema=InputState)
    _ = builder.add_node("prepare", nodes.prepare)
    _ = builder.add_node("agent", nodes.react)
    _ = builder.add_node("tools", ToolNode(tools))
    _ = builder.add_node("reason", nodes.reason)
    _ = builder.add_node("publish", nodes.persist)
    _ = builder.add_edge(START, "prepare")
    _ = builder.add_edge("prepare", "agent")
    _ = builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "reason"})
    _ = builder.add_edge("tools", "agent")
    _ = builder.add_edge("reason", "publish")
    _ = builder.add_edge("publish", END)
    return builder.compile(checkpointer=checkpointer, name="TRACE ReAct Agent")


trace = build_graph(MCPEvidence(Settings()))
investigator = trace
