# Copyright 2026 TRACE contributors
"""Deterministic model responses with real graph and MCP execution."""

from collections import deque
from dataclasses import dataclass, field
from typing import Final
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import FastMCPTransport
from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from pydantic import JsonValue

from trace_agent import evidence as transport
from trace_agent.config import Settings
from trace_agent.errors import ContractError
from trace_agent.evidence import MCPEvidence
from trace_agent.models import (
    CandidateDraft,
    Context,
    LiveInvestigation,
    Proposal,
    Publication,
    Receipt,
)

ALERT: Final = (
    "[경보] ETCH-02 / CH-A / Lot LOT-1 / Wafer W01 / RCP-1\n"
    "- 15:15:11 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)\n"
    "- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W "
    "(한계 37 W) (OCAP-ETCH-RF)\n"
    "- source_rf_reflected_w (W, 정상 5.364±0.590): 5.2 - 44.1\n"
    "unknown observations retained"
)


def draft(identity: UUID | None = None, action: str = "Inspect matching network") -> CandidateDraft:
    return CandidateDraft(
        id=identity,
        cause="RF mismatch",
        action=action,
        rationale="Elevated reflected power; compare the matching network.",
        checks=["Compare reflected power"],
        case_ids=["CASE-1"],
        doc_ids=["DOC-1"],
        unknowns=["No physical inspection yet"],
    )


@dataclass(slots=True)
class ScriptedModel:
    """Mutable response queues are consumed by the actual graph, not a graph mock."""

    responses: deque[AIMessage] = field(default_factory=deque)
    proposal: Proposal = field(default_factory=lambda: Proposal(summary="RF", candidates=[draft()]))
    seen: list[list[AnyMessage]] = field(default_factory=list)

    async def react(self, messages: list[AnyMessage], config: RunnableConfig) -> AIMessage:
        del config
        self.seen.append(messages)
        return (
            self.responses.popleft()
            if self.responses
            else AIMessage(content="Investigation answer")
        )

    async def propose(
        self, messages: list[AnyMessage], config: RunnableConfig, candidate_ids: list[UUID]
    ) -> Proposal:
        del messages, config, candidate_ids
        return self.proposal


@dataclass(slots=True)
class Business:
    """Stateful external-service substitute behind the real FastMCP protocol."""

    server: FastMCP = field(default_factory=lambda: FastMCP("test-business"))
    records: dict[UUID, LiveInvestigation] = field(default_factory=dict)
    writes: list[tuple[UUID, Publication]] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    fail_publication: bool = False

    def register(self) -> None:
        @self.server.tool
        async def search_cases(context: Context) -> list[dict[str, JsonValue]]:
            self.calls.append("search_cases")
            return [
                {
                    "id": "CASE-1",
                    "equipment": context.equipment or "ETCH-02",
                    "chamber": "CH-A",
                    "recipe": "RCP-1",
                    "symptom": "RF reflection",
                    "metrics": {"source_rf_reflected_w": 5.0},
                    "cause": "RF mismatch",
                    "action": "Inspect matching network",
                    "docs": ["DOC-1"],
                    "score": 0.8,
                }
            ]

        @self.server.tool
        async def upsert_live_investigation(thread_id: UUID, payload: Publication) -> Receipt:
            self.calls.append("upsert_live_investigation")
            if self.fail_publication:
                raise ContractError(detail="Business unavailable")
            current = self.records.get(thread_id)
            if payload.base_revision != (current.revision if current else 0):
                raise ContractError(detail="Stale revision")
            if current and current.alert != payload.alert:
                raise ContractError(detail="Alert changed")
            ids = [candidate.id for candidate in payload.candidates]
            if len(set(ids)) != len(ids):
                raise ContractError(detail="Duplicate candidate")
            self.writes.append((thread_id, payload))
            self.records[thread_id] = LiveInvestigation(
                id=thread_id,
                thread_id=thread_id,
                alert=payload.alert,
                summary=payload.summary,
                candidates=payload.candidates,
                revision=payload.base_revision + 1,
                approval=current.approval if current else None,
                created_at="2026-10-23T00:00:00Z",
                updated_at="2026-10-23T00:00:01Z",
                demo=True,
            )
            return Receipt(id=thread_id, thread_id=thread_id, revision=payload.base_revision + 1)

        @self.server.tool
        async def get_live_investigation(thread_id: UUID) -> LiveInvestigation:
            self.calls.append("get_live_investigation")
            return self.records[thread_id]

    def client(self, url: str, timeout: int) -> Client[FastMCPTransport]:
        del url
        return Client(self.server, timeout=timeout)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def business(monkeypatch: pytest.MonkeyPatch) -> Business:
    server = Business()
    server.register()
    monkeypatch.setattr(transport, "Client", server.client)
    return server


@pytest.fixture
def evidence(business: Business) -> MCPEvidence:
    del business
    return MCPEvidence(Settings())
