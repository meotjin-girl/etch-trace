"""MCP-only business evidence access; no business database connection."""

from dataclasses import dataclass
from typing import Protocol

import anyio
from fastmcp import Client
from pydantic import BaseModel

from .models import Case, Context, Document, Metric


class ToolEnvelope[T](BaseModel):
    result: list[T]


class EvidenceProvider(Protocol):
    def search_cases(self, context: Context) -> list[Case]: ...

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]: ...

    def search_documents(self, document_ids: list[str]) -> list[Document]: ...


def mcp_url(base: str) -> str:
    """Accept either a service base URL or its explicit MCP endpoint."""
    base = base.rstrip("/")
    return base if base.endswith("/mcp") else f"{base}/mcp"


@dataclass(frozen=True, slots=True)
class MCPEvidenceProvider:
    business_url: str
    rag_url: str

    async def _search_cases(self, context: Context) -> list[Case]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "search_cases", {"context": context.model_dump(exclude_none=True)},
            )
        return ToolEnvelope[Case].model_validate(result.structured_content).result

    async def _analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "analyze_metrics",
                {"cases": [case.model_dump() for case in cases], "metrics": context.metrics},
            )
        return ToolEnvelope[Metric].model_validate(result.structured_content).result

    async def _search_documents(self, document_ids: list[str]) -> list[Document]:
        async with Client(mcp_url(self.rag_url)) as client:
            result = await client.call_tool(
                "search_documents", {"document_ids": document_ids},
            )
        return ToolEnvelope[Document].model_validate(result.structured_content).result

    def search_cases(self, context: Context) -> list[Case]:
        return anyio.run(self._search_cases, context)

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        return anyio.run(self._analyze_metrics, cases, context)

    def search_documents(self, document_ids: list[str]) -> list[Document]:
        return anyio.run(self._search_documents, document_ids)
