# Copyright 2026 TRACE contributors
"""Request preparation, structured reasoning, and mandatory publication."""

from dataclasses import dataclass
from typing import assert_never
from uuid import UUID, uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import TypeAdapter

from .alert_text import parse_alert_text
from .errors import ContractError
from .evidence import Evidence, publish, read_live
from .model import Reasoner
from .models import Alert, Candidate, Publication, Request
from .prompts import PROPOSAL_PROMPT, SYSTEM_PROMPT, investigation_data
from .state import State


def thread_id(config: RunnableConfig) -> UUID:
    """Identity comes exclusively from server execution configuration."""
    return TypeAdapter(UUID).validate_python(config.get("configurable", {}).get("thread_id"))


@dataclass(frozen=True, slots=True)
class Nodes:
    """Graph dependencies shared across node executions."""

    evidence: Evidence
    model: Reasoner

    async def prepare(self, state: State, config: RunnableConfig) -> State:
        """Consume an envelope once and refresh authoritative business state."""
        identity = thread_id(config)
        update: State = {"request": None, "proposal": None}
        if state.get("revision", 0):
            live = await read_live(self.evidence, identity)
            if live.alert != state.get("alert"):
                raise ContractError(detail="The immutable alert differs from business readback.")
            update.update(
                alert=live.alert,
                summary=live.summary,
                candidates=live.candidates,
                revision=live.revision,
                approval=live.approval,
            )
        request = state.get("request")
        if request is not None:
            incoming = Request.model_validate(request)
            match incoming.role:
                case "system":
                    if state.get("alert") is not None:
                        raise ContractError(detail="A thread's alert cannot be replaced.")
                    parsed = parse_alert_text(incoming.content)
                    update.update(alert=parsed.alert, parsed_alert=parsed, context=parsed.context())
                case "user":
                    pass
                case _:
                    assert_never(incoming.role)
            update["messages"] = [HumanMessage(content=incoming.content)]
        elif not state.get("messages"):
            raise ContractError(detail="Supply a request envelope or a user message.")
        return update

    async def react(self, state: State, config: RunnableConfig) -> State:
        """One ReAct model turn; evidence remains in the checkpointed conversation."""
        response = await self.model.react(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=investigation_data(state)),
                *state.get("messages", []),
            ],
            config,
        )
        return {"messages": [response]}

    async def reason(self, state: State, config: RunnableConfig) -> State:
        """Generate typed reasoning after the ordinary ReAct tool loop finishes."""
        proposal = await self.model.propose(
            [
                SystemMessage(content=PROPOSAL_PROMPT),
                HumanMessage(content=investigation_data(state)),
                *state.get("messages", []),
            ],
            config,
            [candidate.id for candidate in state.get("candidates", [])],
        )
        return {"proposal": proposal}

    async def persist(self, state: State, config: RunnableConfig) -> State:
        """Assign UUIDs and publish changed proposals; no tool or model can skip this node."""
        proposal = state.get("proposal")
        if proposal is None:
            raise ContractError(detail="The reasoning node did not produce a structured proposal.")
        previous = state.get("candidates", [])
        if proposal.candidates is None:
            if state.get("alert") is not None and not previous:
                raise ContractError(detail="An initial alert investigation requires proposals.")
            return {"proposal": None}
        if not proposal.candidates:
            raise ContractError(detail="A candidate replacement cannot be empty.")
        known = {candidate.id for candidate in previous}
        seen: set[UUID] = set()
        candidates: list[Candidate] = []
        for draft in proposal.candidates:
            if draft.id is not None and draft.id not in known:
                raise ContractError(
                    detail="A candidate ID must be existing or null for a new candidate."
                )
            identity = draft.id if draft.id is not None else uuid4()
            if identity in seen:
                raise ContractError(detail="Duplicate candidate IDs are not allowed.")
            seen.add(identity)
            candidates.append(
                Candidate(
                    id=identity,
                    cause=draft.cause,
                    action=draft.action,
                    rationale=draft.rationale,
                    checks=draft.checks,
                    case_ids=draft.case_ids,
                    doc_ids=draft.doc_ids,
                    unknowns=draft.unknowns,
                )
            )
        if candidates == previous:
            return {"proposal": None}
        alert = state.get("alert")
        if alert is None:
            # User-initiated investigations have no equipment identifiers to invent.
            first = next(
                message
                for message in state.get("messages", [])
                if isinstance(message, HumanMessage)
            )
            alert = Alert(
                tool_id="",
                chamber_id="",
                lot_id="",
                wafer_id="",
                recipe_id="",
                source_text=first.text,
            )
        payload = Publication(
            base_revision=state.get("revision", 0),
            alert=alert,
            summary=proposal.summary,
            candidates=candidates,
        )
        receipt = await publish(self.evidence, thread_id(config), payload)
        return {
            "alert": alert,
            "summary": proposal.summary,
            "candidates": candidates,
            "revision": receipt.revision,
            "proposal": None,
        }
