"""Strict HTTP boundaries for live investigations and approved snapshots."""

from datetime import datetime
from typing import Literal, override
from uuid import UUID

from pydantic import Field, field_validator
from v1_models import Input


class Alert(Input):
    tool_id: str
    chamber_id: str
    lot_id: str
    wafer_id: str
    recipe_id: str
    source_text: str


class Candidate(Input):
    id: UUID
    cause: str
    action: str
    rationale: str
    checks: tuple[str, ...]
    case_ids: tuple[str, ...]
    doc_ids: tuple[str, ...]
    unknowns: tuple[str, ...]


class DuplicateCandidates(ValueError):
    @override
    def __str__(self) -> str:
        return "Candidate IDs must be unique"


class LiveInput(Input):
    base_revision: int = Field(ge=0, strict=True)
    alert: Alert
    summary: str
    candidates: tuple[Candidate, ...] = Field(min_length=1)
    demo: Literal[True]

    @field_validator("candidates")
    @classmethod
    def unique_candidates(cls, value: tuple[Candidate, ...]) -> tuple[Candidate, ...]:
        if len({candidate.id for candidate in value}) != len(value):
            raise DuplicateCandidates()
        return value


class ApprovalInput(Input):
    candidate_id: UUID
    expected_revision: int = Field(ge=1, strict=True)
    comment: str = ""


class Approval(Input):
    revision: int
    candidate: Candidate
    approved_by_id: str
    approved_by: str
    approved_at: datetime
    comment: str


class ActionInput(Input):
    content: str = Field(min_length=1, max_length=10000)
    result: str = Field(min_length=1, max_length=10000)

    @field_validator("content", "result")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ActionRecord(Input):
    content: str
    result: str
    recorded_by_id: str
    recorded_by: str
    recorded_at: datetime


class LiveResult(Input):
    id: UUID
    thread_id: UUID
    revision: int


class Investigation(LiveResult):
    alert: Alert
    summary: str
    candidates: tuple[Candidate, ...]
    approval: Approval | None
    action: ActionRecord | None = None
    created_at: datetime
    updated_at: datetime
    demo: Literal[True] = True


class InvestigationSummary(LiveResult):
    tool_id: str
    chamber_id: str
    lot_id: str
    summary: str
    candidate_count: int
    approved_at: datetime | None
    action_recorded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    demo: Literal[True] = True
