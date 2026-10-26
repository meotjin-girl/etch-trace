# Copyright 2026 TRACE contributors
"""The public graph contract, rather than a mocked node pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastmcp.exceptions import ToolError
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import TypeAdapter

from trace_agent.graph import build_graph
from trace_agent.models import ActionRecord, Approval, Proposal, Request
from trace_agent.state import State

from .conftest import ALERT, Business, ScriptedModel, draft

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from trace_agent.evidence import MCPEvidence

pytestmark = pytest.mark.anyio


async def test_react_loop_publishes_initial_candidates(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: a real graph, a real MCP tool, and one model-requested tool call.
    model = ScriptedModel()
    model.responses.append(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_cases",
                    "args": {"context": {"equipment": "ETCH-02"}},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        )
    )
    identity = uuid4()
    graph = build_graph(evidence, model, InMemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}

    # When: an initial system envelope runs through the compiled graph.
    raw = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    state = TypeAdapter(State).validate_python(raw)

    # Then: the tool result returns to the model and publication is mandatory.
    assert len(model.seen) == 2
    assert any(isinstance(message, ToolMessage) for message in model.seen[1])
    assert business.calls == ["search_cases", "upsert_live_investigation"]
    assert business.records[identity].candidates[0].id.version == 4
    assert state.get("revision") == 1
    assert "request" in state
    assert state["request"] is None
    assert [m.content for m in state.get("messages", []) if isinstance(m, HumanMessage)] == [ALERT]


async def test_followup_updates_same_record_and_preserves_existing_candidate_id(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: a persisted initial conversation.
    identity = uuid4()
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}
    model = ScriptedModel()
    saver = InMemorySaver()
    graph = build_graph(evidence, model, saver)
    _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    candidate = business.records[identity].candidates[0]
    model.proposal = Proposal(
        summary="Revised", candidates=[draft(candidate.id, "Inspect RF cable")]
    )
    restored = build_graph(evidence, model, saver)

    # When: another compiled instance resumes the same checkpoint thread.
    result = TypeAdapter(State).validate_python(
        await restored.ainvoke(
            {"request": Request(role="user", content="Revise the action")}, config
        )
    )

    # Then: the same record advances once and conversation history survives.
    assert list(business.records) == [identity]
    assert [payload.base_revision for _, payload in business.writes] == [0, 1]
    assert business.records[identity].candidates[0].id == candidate.id
    assert business.records[identity].candidates[0].action == "Inspect RF cable"
    assert result.get("revision") == 2
    assert [m.content for m in result.get("messages", []) if isinstance(m, HumanMessage)] == [
        ALERT,
        "Revise the action",
    ]


@pytest.mark.parametrize("recorded", [False, True])
async def test_general_question_reads_approval_without_replacing_candidates(
    evidence: MCPEvidence, business: Business, *, recorded: bool
) -> None:
    # Given: an externally approved investigation.
    identity = uuid4()
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}
    model = ScriptedModel()
    graph = build_graph(evidence, model, InMemorySaver())
    _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    original = business.records[identity]
    approval = Approval(
        revision=1,
        candidate=original.candidates[0],
        approved_by_id="reviewer-2",
        approved_by="Reviewer",
        approved_at="2026-10-23T00:00:00Z",
        comment="Reviewed",
    )
    business.records[identity] = original.model_copy(
        update={
            "approval": approval,
            "action": ActionRecord(
                content="Checked RF",
                result="Restored",
                recorded_by_id="reviewer-2",
                recorded_by="Reviewer",
                recorded_at="2026-10-23T00:00:00Z",
            )
            if recorded
            else None,
        }
    )
    model.proposal = Proposal(summary="No replacement", candidates=None)

    # When: standard message input continues the approved conversation.
    result = TypeAdapter(State).validate_python(
        await graph.ainvoke(
            {"messages": [HumanMessage(content="Explain the approved cause")]}, config
        )
    )

    # Then: approval is refreshed without a new revision or duplicated alert.
    assert result.get("approval") == approval
    assert result.get("candidates") == original.candidates
    assert len(business.writes) == 1
    assert business.calls[-1] == "get_live_investigation"
    assert len([m for m in result.get("messages", []) if isinstance(m, HumanMessage)]) == 2


async def test_edit_after_approval_preserves_snapshot(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: a business-approved candidate.
    identity = uuid4()
    config: RunnableConfig = {"configurable": {"thread_id": str(identity)}}
    model = ScriptedModel()
    graph = build_graph(evidence, model, InMemorySaver())
    _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    original = business.records[identity]
    approval = Approval(
        revision=1,
        candidate=original.candidates[0],
        approved_by_id="r2",
        approved_by="Reviewer",
        approved_at="2026-10-23T00:00:00Z",
        comment="",
    )
    business.records[identity] = original.model_copy(update={"approval": approval})
    model.proposal = Proposal(
        summary="Updated", candidates=[draft(original.candidates[0].id, "New")]
    )

    # When: a user edits the proposal after approval.
    _ = await graph.ainvoke({"request": Request(role="user", content="Revise")}, config)

    # Then: current proposals change while the approved snapshot stays immutable.
    assert business.records[identity].revision == 2
    assert business.records[identity].approval == approval
    assert business.records[identity].candidates[0].action == "New"


async def test_publication_failure_fails_run_without_success_state(
    evidence: MCPEvidence, business: Business
) -> None:
    # Given: an unavailable business publication boundary.
    business.fail_publication = True
    graph = build_graph(evidence, ScriptedModel(), InMemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": str(uuid4())}}

    # When / Then: the actual graph fails rather than inventing a saved revision.
    with pytest.raises(ToolError, match="Business unavailable"):
        _ = await graph.ainvoke({"request": Request(role="system", content=ALERT)}, config)
    assert business.records == {}
    snapshot = await graph.aget_state(config)
    state = TypeAdapter(State).validate_python(snapshot.values)
    assert state.get("revision", 0) == 0
