"""MCP-only business evidence access; no business database connection."""

from dataclasses import dataclass
from typing import Protocol

import anyio
from fastmcp import Client
from pydantic import BaseModel, JsonValue

from .models import Case, Context, Document, Metric, PhysicsResult, Requester


class ToolEnvelope[T](BaseModel):
    result: list[T]


class EvidenceProvider(Protocol):
    def search_cases(self, context: Context) -> list[Case]: ...

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]: ...

    def search_documents(self, document_ids: list[str]) -> list[Document]: ...

    def evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]: ...


class HistoryEvidenceReader(Protocol):
    def list_investigations(self, requester: Requester) -> list[dict[str, JsonValue]]: ...


class SopRagSearcher(Protocol):
    def search_sop(self, query: str) -> list[Document]: ...


def mcp_url(base: str) -> str:
    """Accept either a service base URL or its explicit MCP endpoint."""
    base = base.rstrip("/")
    return base if base.endswith("/mcp") else f"{base}/mcp"


@dataclass(frozen=True, slots=True)
class MCPEvidenceProvider:
    business_url: str
    rag_url: str
    physics_url: str = ""

    async def _search_cases(self, context: Context) -> list[Case]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "search_cases", {"context": {
                    key: value for key, value in context.model_dump(exclude_none=True).items()
                    if key != "physics"
                }},
            )
        return ToolEnvelope[Case].model_validate(result.structured_content).result

    async def _analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "analyze_metrics",
                {
                    "cases": [case.model_dump() for case in cases],
                    "metrics": context.metrics,
                },
            )
        return ToolEnvelope[Metric].model_validate(result.structured_content).result

    async def _search_documents(self, document_ids: list[str]) -> list[Document]:
        async with Client(mcp_url(self.rag_url)) as client:
            result = await client.call_tool(
                "search_documents", {"document_ids": document_ids},
            )
        return ToolEnvelope[Document].model_validate(result.structured_content).result

    async def _search_sop(self, query: str) -> list[Document]:
        async with Client(mcp_url(self.rag_url)) as client:
            result = await client.call_tool("search_sop", {"query": query})
        return ToolEnvelope[Document].model_validate(result.structured_content).result

    async def _list_investigations(
        self, requester: Requester,
    ) -> list[dict[str, JsonValue]]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool("list_investigations", {
                "user_name": requester.name, "user_role": requester.role,
            })
        return ToolEnvelope[dict[str, JsonValue]].model_validate(
            result.structured_content,
        ).result

    async def _evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]:
        async with Client(mcp_url(self.physics_url)) as client:
            result = await client.call_tool(
                "evaluate_etch_physics", {"inputs": context.physics.model_dump()},
            )
        return ToolEnvelope[PhysicsResult].model_validate(result.structured_content).result

    def search_cases(self, context: Context) -> list[Case]:
        return anyio.run(self._search_cases, context)

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        return anyio.run(self._analyze_metrics, cases, context)

    def search_documents(self, document_ids: list[str]) -> list[Document]:
        return anyio.run(self._search_documents, document_ids)

    def search_sop(self, query: str) -> list[Document]:
        return anyio.run(self._search_sop, query)

    def evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]:
        return anyio.run(self._evaluate_etch_physics, context)

    def list_investigations(
        self, requester: Requester,
    ) -> list[dict[str, JsonValue]]:
        return anyio.run(self._list_investigations, requester)
