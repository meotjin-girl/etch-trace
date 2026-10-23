# Copyright 2026 TRACE contributors
"""Checkpoint state and a deliberately narrow public input schema."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from .alert_text import ParsedAlert
from .models import Alert, Approval, Candidate, Context, Proposal, Request


class InputState(TypedDict, total=False):
    """Clients may append messages or submit an envelope, never overwrite proposals."""

    messages: Annotated[list[AnyMessage], add_messages]
    request: Request | None


class State(InputState, total=False):
    """One thread owns its conversation and the current business revision."""

    alert: Alert
    parsed_alert: ParsedAlert
    context: Context
    summary: str
    candidates: list[Candidate]
    revision: int
    approval: Approval | None
    proposal: Proposal | None
