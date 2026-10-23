# Copyright 2026 TRACE contributors
# Typed overloads for ChatOpenAI calls used here; implementation stays upstream.

from collections.abc import Sequence
from typing import Literal, overload

from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, JsonValue, SecretStr

class ChatOpenAI:
    def __init__(
        self, *, model: str, api_key: SecretStr, timeout: float, max_retries: int
    ) -> None: ...
    def bind_tools(self, tools: Sequence[BaseTool]) -> Runnable[list[AnyMessage], AIMessage]: ...
    @overload
    def with_structured_output[T: BaseModel](
        self, schema: type[T], *, method: Literal["json_schema"], strict: bool
    ) -> Runnable[list[AnyMessage], T]: ...
    @overload
    def with_structured_output(
        self, schema: dict[str, JsonValue], *, method: Literal["json_schema"], strict: bool
    ) -> Runnable[list[AnyMessage], dict[str, JsonValue]]: ...
