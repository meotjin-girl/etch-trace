# Copyright 2026 TRACE contributors
"""Validated business wire contracts and structured model proposals."""

from datetime import datetime
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


class ActionRecord(Model):
    """Backend-owned record of the engineer's completed action."""

    content: str
    result: str
    recorded_by_id: str
    recorded_by: str
    recorded_at: datetime


class LiveInvestigation(Model):
    """Business MCP readback, including independent approval history."""

    id: UUID
    thread_id: UUID
    alert: Alert
    summary: str
    candidates: list[Candidate]
    revision: int = Field(ge=1)
    approval: Approval | None
    action: ActionRecord | None = None
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


class PhysicsControlLimit(Model):
    """Approved numeric limits supplied by an authorized source."""

    lower: float | None = None
    upper: float | None = None
    unit: str
    approved: bool = False
    document_id: str | None = None
    revision: str | None = None


class PhysicsRateInterval(Model):
    """An explicit measured or simulated etch-rate interval."""

    start_sec: float
    end_sec: float
    etch_rate_nm_min: float
    origin: Literal["MEASURED", "SIMULATED"]
    source: str


class PhysicsRateSeriesInputs(Model):
    intervals: list[PhysicsRateInterval] = Field(default_factory=list)


class PhysicsMetrologyComparisonInputs(Model):
    measured_value: float | None = None
    expected_value: float | None = None
    unit: str = "nm"
    measured_key: str = "measured_etch_depth_nm"
    expected_key: str = "target_etch_depth_nm"
    measurement_source: str = "metrology"
    expected_source: str = "recipe_target"
    control_limit: PhysicsControlLimit | None = None


class PhysicsReferenceObservation(Model):
    run_id: str
    equipment: str
    chamber: str
    recipe: str
    step: str
    ended_at: datetime
    measurement_condition_id: str
    value: float
    unit: str
    normal: bool = True


class PhysicsReferenceComparisonInputs(Model):
    target_run_id: str
    equipment: str
    chamber: str
    recipe: str
    step: str
    target_started_at: datetime
    measurement_condition_id: str
    target_value: float
    unit: str
    references: list[PhysicsReferenceObservation] = Field(default_factory=list)
    minimum_reference_runs: int = Field(default=3, ge=2)
    measurement_resolution: float | None = Field(default=None, gt=0)
    control_limit: PhysicsControlLimit | None = None


class PhysicsQuantitativeInputs(Model):
    measured_etch_depth_nm: float | None = None
    target_etch_depth_nm: float | None = None
    depth_control_limit: PhysicsControlLimit | None = None
    rate_intervals: list[PhysicsRateInterval] = Field(default_factory=list)


class PhysicsProcessConditionPoint(Model):
    offset_sec: float
    source_rf_w: float
    source_rf_reference_w: float
    bias_rf_w: float
    bias_rf_reference_w: float
    pressure_mtorr: float
    pressure_reference_mtorr: float
    sf6_sccm: float
    sf6_reference_sccm: float
    o2_sccm: float
    o2_reference_sccm: float
    esc_temp_c: float
    esc_temp_reference_c: float
    source: str | None = None


class PhysicsSensitivityCoefficient(Model):
    variable: Literal["source_rf", "bias_rf", "pressure", "sf6", "o2", "esc_temp"]
    value: float
    unit: Literal["per_relative_change"] | None = None
    source: str | None = None
    calibrated: Literal[False] | None = None


class PhysicsEducationalSimulationInputs(Model):
    base_etch_rate_nm_min: float | None = None
    feature_width_nm: float | None = None
    arde_coefficient: float | None = None
    arde_coefficient_source: str | None = None
    process_points: list[PhysicsProcessConditionPoint] | None = None
    coefficients: list[PhysicsSensitivityCoefficient] | None = None
    source_run_id: str | None = None


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
