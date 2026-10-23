# Copyright 2026 TRACE contributors
"""Validated business wire contracts and structured model proposals."""

from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    """Immutable, closed business boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class Request(Model):
    """An alert envelope is data, never an LLM system instruction."""

    role: Literal["system", "user"]
    content: str = Field(min_length=1)


class Alert(Model):
    """Immutable identifiers and verbatim original observations."""

    tool_id: str
    chamber_id: str
    lot_id: str
    wafer_id: str
    recipe_id: str
    source_text: str


class Reasoning(Model):
    """Evidence-backed, human-reviewable cause/action justification."""

    cause: str = Field(min_length=1)
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    checks: list[str]
    case_ids: list[str]
    doc_ids: list[str]
    unknowns: list[str]


class Candidate(Reasoning):
    """Published candidate identity is owned by code."""

    id: UUID


class CandidateDraft(Reasoning):
    """Null allocates a new ID; an existing UUID explicitly preserves identity."""

    id: UUID | None


class Proposal(Model):
    """Null candidates means no proposal change, not an empty replacement."""

    summary: str
    candidates: list[CandidateDraft] | None


class Approval(Model):
    """Backend-owned immutable approval snapshot."""

    revision: int
    candidate: Candidate
    approved_by_id: str
    approved_by: str
    approved_at: str
    comment: str


class LiveInvestigation(Model):
    """Business MCP readback, including independent approval history."""

    id: UUID
    thread_id: UUID
    alert: Alert
    summary: str
    candidates: list[Candidate]
    revision: int = Field(ge=1)
    approval: Approval | None
    created_at: str
    updated_at: str
    demo: Literal[True]


class Publication(Model):
    """Optimistic full replacement submitted only when proposals change."""

    base_revision: int = Field(ge=0)
    alert: Alert
    summary: str
    candidates: list[Candidate] = Field(min_length=1)
    demo: Literal[True] = True


class Receipt(Model):
    """Identity and next revision returned by the business service."""

    id: UUID
    thread_id: UUID
    revision: int = Field(ge=1)


class Context(Model):
    """Case search arguments accepted by Business MCP."""

    equipment: str | None = None
    chamber: str | None = None
    recipe: str | None = None
    symptom: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class PhysicsInputs(Model):
    """Only supplied physical inputs, with their provenance."""

    etch_rate_nm_min: float | None = None
    etch_time_sec: float | None = None
    pre_thickness_nm: float | None = None
    post_thickness_nm: float | None = None
    target_etch_rate_nm_min: float | None = None
    mask_etch_rate_nm_min: float | None = None
    sources: dict[str, str] = Field(default_factory=dict)


class Case(BaseModel):
    """Case boundary preserves additional MCP evidence fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")
    id: str
    equipment: str
    chamber: str
    recipe: str
    symptom: str
    metrics: dict[str, float]
    cause: str
    action: str
    docs: list[str]
