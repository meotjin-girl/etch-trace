# Copyright 2026 TRACE contributors
"""Standard ChatOpenAI tool calling and schema-constrained proposal output."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import JsonValue, TypeAdapter

from .config import Settings
from .errors import ConfigurationError
from .models import Proposal


class Reasoner(Protocol):
    """The model-only seam; graph routing, tools, and persistence remain real."""

    async def react(self, messages: list[AnyMessage], config: RunnableConfig) -> AIMessage:
        """Produce either tool calls or a conversational answer."""
        ...

    async def propose(
        self, messages: list[AnyMessage], config: RunnableConfig, candidate_ids: list[UUID]
    ) -> Proposal:
        """Return a validated proposal, not parsed conversational prose."""
        ...


@dataclass(frozen=True, slots=True)
class OpenAIReasoner:
    """Use the installed OpenAI integration, including its streaming callbacks."""

    settings: Settings
    tools: list[BaseTool]

    def client(self) -> ChatOpenAI:
        """Fail at execution when the API key is absent, never invent a result."""
        if not self.settings.openai_api_key.get_secret_value():
            raise ConfigurationError(variable="OPENAI_API_KEY")
        return ChatOpenAI(
            model=self.settings.openai_model or "gpt-4.1-mini",
            api_key=self.settings.openai_api_key,
            timeout=90,
            max_retries=0,
        )

    async def react(self, messages: list[AnyMessage], config: RunnableConfig) -> AIMessage:
        """Run one standard asynchronous tool-calling turn."""
        response = await self.client().bind_tools(self.tools).ainvoke(messages, config)
        return AIMessage.model_validate(response)

    async def propose(
        self, messages: list[AnyMessage], config: RunnableConfig, candidate_ids: list[UUID]
    ) -> Proposal:
        """Constrain IDs to existing candidates; only code allocates new UUIDs."""
        object_schema = TypeAdapter(dict[str, JsonValue])
        schema = object_schema.validate_python(Proposal.model_json_schema())
        definitions = object_schema.validate_python(schema["$defs"])
        draft = object_schema.validate_python(definitions["CandidateDraft"])
        properties = object_schema.validate_python(draft["properties"])
        properties["id"] = {
            "type": ["string", "null"],
            "enum": [None, *[str(identity) for identity in candidate_ids]],
        }
        draft["properties"] = properties
        definitions["CandidateDraft"] = draft
        schema["$defs"] = definitions
        response = (
            await self.client()
            .with_structured_output(schema, method="json_schema", strict=True)
            .ainvoke(messages, config)
        )
        return Proposal.model_validate(response)
