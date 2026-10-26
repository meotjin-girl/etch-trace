# Copyright 2026 TRACE contributors
"""Async MCP transport; business persistence is never an optional model tool."""

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from fastmcp import Client
from pydantic import JsonValue, TypeAdapter

from .config import Settings
from .errors import ContractError
from .models import LiveInvestigation, Publication, Receipt

type Service = Literal["business", "rag", "physics", "sensor"]


class Evidence(Protocol):
    """Small transport seam shared by real MCP and in-process test MCP servers."""

    async def call(self, service: Service, name: str, arguments: dict[str, JsonValue]) -> JsonValue:
        """Call a remote tool and return its structured JSON result."""
        ...


@dataclass(frozen=True, slots=True)
class MCPEvidence:
    """One context-managed async MCP session per call, with a bounded timeout."""

    settings: Settings

    async def call(self, service: Service, name: str, arguments: dict[str, JsonValue]) -> JsonValue:
        """Unwrap only FastMCP's standard result envelope."""
        urls: dict[Service, str] = {
            "business": self.settings.business_mcp_url,
            "rag": self.settings.rag_mcp_url,
            "physics": self.settings.physics_mcp_url,
            "sensor": self.settings.sensor_mcp_url,
        }
        base = urls[service].rstrip("/")
        url = base if base.endswith("/mcp") else f"{base}/mcp"
        async with Client(url, timeout=60) as client:
            result = await client.call_tool(name, arguments)
        data = TypeAdapter(JsonValue).validate_python(result.structured_content)
        if isinstance(data, dict) and set(data) == {"result"}:
            return data["result"]
        if data is None:
            raise ContractError(detail=f"{name} returned no structured MCP content.")
        return data


async def read_live(evidence: Evidence, thread_id: UUID) -> LiveInvestigation:
    """Refresh authoritative proposals and immutable approval before followups."""
    result = await evidence.call(
        "business", "get_live_investigation", {"thread_id": str(thread_id)}
    )
    live = LiveInvestigation.model_validate(result)
    if live.id != thread_id or live.thread_id != thread_id:
        raise ContractError(detail="Business readback identity differs from the trusted thread ID.")
    return live


async def publish(evidence: Evidence, thread_id: UUID, payload: Publication) -> Receipt:
    """Publish a complete replacement with code-owned identity and optimistic revision."""
    result = await evidence.call(
        "business",
        "upsert_live_investigation",
        {
            "thread_id": str(thread_id),
            "payload": TypeAdapter(dict[str, JsonValue]).validate_python(
                payload.model_dump(mode="json")
            ),
        },
    )
    receipt = Receipt.model_validate(result)
    if (
        receipt.id != thread_id
        or receipt.thread_id != thread_id
        or receipt.revision != payload.base_revision + 1
    ):
        raise ContractError(
            detail="Business publication returned an inconsistent identity or revision."
        )
    return receipt
