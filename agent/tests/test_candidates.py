# Copyright 2026 TRACE contributors
"""Identity and replacement invariants exercised through the real graph."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr, ValidationError

from trace_agent.config import Settings
from trace_agent.errors import ConfigurationError, ContractError
from trace_agent.graph import build_graph
from trace_agent.model import OpenAIReasoner
from trace_agent.models import CandidateDraft, Proposal, Request

from .conftest import ALERT, Business, ScriptedModel, draft

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from trace_agent.evidence import MCPEvidence

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("mode", ["unknown", "duplicate", "empty", "unchanged"])
async def test_candidate_replacement_enforces_existing_identity(
    mode: str, evidence: MCPEvidence, business: Business
) -> None:
    # Given: a known candidate in an existing thread.
    identity = uuid4()
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}
    model = ScriptedModel()
    graph = build_graph(evidence, model, InMemorySaver())
    _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    existing = draft(business.records[identity].candidates[0].id)
    variants = {
        "unknown": [draft(uuid4())],
        "duplicate": [existing, existing],
        "empty": [],
        "unchanged": [existing],
    }
    model.proposal = Proposal(
        summary="Different summary alone is not a change", candidates=variants[mode]
    )

    # When: a replacement is attempted.
    if mode == "unchanged":
        _ = await graph.ainvoke({"request": Request(role="user", content="Explain")}, config)
    else:
        with pytest.raises(ContractError):
            _ = await graph.ainvoke({"request": Request(role="user", content="Revise")}, config)

    # Then: invalid or identical proposals never create another business revision.
    assert len(business.writes) == 1
    assert business.records[identity].revision == 1


async def test_new_candidate_gets_new_uuid_while_retained_candidate_keeps_id(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: an existing candidate and an additional null-ID draft.
    identity = uuid4()
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}
    model = ScriptedModel()
    graph = build_graph(evidence, model, InMemorySaver())
    _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    old_id = business.records[identity].candidates[0].id
    model.proposal = Proposal(
        summary="Two", candidates=[draft(old_id), draft(action="Inspect chamber")]
    )

    # When: the complete changed list is published.
    _ = await graph.ainvoke({"request": Request(role="user", content="Add alternative")}, config)

    # Then: code allocates only the new identity and retains the full list.
    candidates = business.records[identity].candidates
    assert [item.id for item in candidates[:1]] == [old_id]
    assert candidates[1].id != old_id
    assert candidates[1].id.version == 4
    assert len(business.writes[-1][1].candidates) == 2


async def test_initial_alert_cannot_finish_without_proposals(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: a model attempting to skip initial publication.
    model = ScriptedModel(proposal=Proposal(summary="", candidates=None))
    graph = build_graph(evidence, model)

    # When / Then: an initial alert fails rather than becoming a conversation-only success.
    with pytest.raises(ContractError, match="requires proposals"):
        _ = await graph.ainvoke(
            {"request": Request(role="system", content=ALERT)},
            {"configurable": {"thread_id": str(uuid4())}},
        )
    assert business.writes == []


async def test_invalid_candidate_uuid_is_rejected_at_schema_boundary() -> None:
    # Given: a model draft whose ID is not a UUID.
    data = draft().model_dump(mode="json")
    data["id"] = "CASE-1"

    # When / Then: typed parsing rejects it before any graph publication.
    with pytest.raises(ValidationError):
        _ = CandidateDraft.model_validate(data)


async def test_missing_openai_key_fails_without_publishing(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: the real ChatOpenAI model adapter without a configured key.
    model = OpenAIReasoner(Settings(openai_api_key=SecretStr("")), [])
    graph = build_graph(evidence, model)

    # When / Then: execution fails clearly and never manufactures candidates.
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        _ = await graph.ainvoke(
            {"request": Request(role="system", content=ALERT)},
            {"configurable": {"thread_id": str(uuid4())}},
        )
    assert business.writes == []


async def test_invalid_thread_uuid_is_rejected_before_model_or_mcp(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: a malformed trusted execution identity.
    model = ScriptedModel()
    graph = build_graph(evidence, model)

    # When / Then: the config boundary fails before external side effects.
    with pytest.raises(ValidationError):
        _ = await graph.ainvoke(
            {"request": Request(role="system", content=ALERT)},
            {"configurable": {"thread_id": "not-a-uuid"}},
        )
    assert model.seen == []
    assert business.calls == []
