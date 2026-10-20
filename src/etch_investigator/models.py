from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    equipment_id: str | None = None
    chamber_id: str | None = None
    event_time: str | None = None
    recipe: str | None = None
    product: str | None = None
    symptom: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    lot_id: str | None = None


class HistoricalCase(BaseModel):
    case_id: str
    equipment_id: str
    chamber_id: str
    event_time: str
    recipe: str
    product: str
    symptom: str
    metrics: dict[str, float]
    root_cause: str
    action: str
    document_refs: list[str]


class ComparableCase(BaseModel):
    case: HistoricalCase
    similarity: float
    match_reasons: list[str]


class MetricAnalysis(BaseModel):
    metric: str
    current: float
    baseline_mean: float
    baseline_std: float
    delta: float
    delta_pct: float | None
    z_score: float | None
    severity: Literal["normal", "watch", "abnormal"]
    supporting_case_ids: list[str]


class EvidenceLink(BaseModel):
    evidence_id: str
    source: str
    excerpt: str
    supports: str


class AgentState(TypedDict, total=False):
    question: str
    request: dict[str, Any]
    query_missing: list[str]
    missing_fields: list[str]
    comparable_cases: list[dict[str, Any]]
    analyses: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    report: str
    answer: str
    wants_report: bool
    review_round: int
    review_notes: list[str]
    status: str

