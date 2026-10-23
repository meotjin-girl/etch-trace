# Copyright 2026 TRACE contributors
# Narrow declarations for supported calls, not runtime replacements.

from collections.abc import Awaitable, Callable
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.prebuilt import ToolNode
from langgraph.types import StateSnapshot

class CompiledStateGraph[S, C, I, O]:
    async def ainvoke(self, input_: I, /, config: RunnableConfig | None = None) -> O: ...
    async def aget_state(self, config: RunnableConfig) -> StateSnapshot: ...

class StateGraph[S, I]:
    def __init__(self, state_schema: type[S], *, input_schema: type[I]) -> None: ...
    def add_node(
        self, node: str, action: Callable[[S, RunnableConfig], Awaitable[S]] | ToolNode
    ) -> StateGraph[S, I]: ...
    def add_edge(self, start_key: str, end_key: str) -> StateGraph[S, I]: ...
    def add_conditional_edges(
        self,
        source: str,
        path: Callable[..., Literal["tools", "__end__"]],
        path_map: dict[str, str],
    ) -> StateGraph[S, I]: ...
    def compile(
        self, checkpointer: BaseCheckpointSaver[str] | None = None, *, name: str | None = None
    ) -> CompiledStateGraph[S, None, I, S]: ...
