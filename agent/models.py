"""Wire models shared by the agent's parser, graph, and HTTP boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

type EventType = Literal[
    "SEARCH_STARTED", "ANALYSIS_STARTED", "REPORT_STARTED",
    "QUESTION", "APPROVAL_REQUIRED", "DONE", "INCOMPLETE", "FAILED",
]


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Context(Model):
    equipment: str | None = None
    chamber: str | None = None
    recipe: str | None = None
    symptom: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class Requester(Model):
    name: str
    role: Literal["worker", "engineer", "admin"]


class HistoryEvidence(Model):
    """Approved, identity-filtered history returned by the Business MCP."""
    id: str
    question: str
    summary: str
    causes: list[str] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)
    approvedBy: str
    approvedAt: str
    eventTime: str | None = None
    lotId: str | None = None


class Case(Model):
    model_config = ConfigDict(frozen=True, extra="allow")
    id: str
    equipment: str
    chamber: str
    recipe: str
    symptom: str
    metrics: dict[str, float]
    cause: str
    action: str
    docs: list[str]
    score: float


class Metric(Model):
    # MCP can attach units and supporting case IDs without losing them here.
    model_config = ConfigDict(frozen=True, extra="allow")
    key: str
    value: float
    mean: float
    std: float
    deltaPct: float
    z: float | None
    severity: str


class Document(Model):
    model_config = ConfigDict(frozen=True, extra="allow")
    id: str
    title: str
    text: str


class InvestigationCheck(Model):
    """A retrieved SOP clause; legacy provisional records remain readable."""
    title: str
    rationale: str
    source: Literal["rag_mcp", "provisional_sop"] = "rag_mcp"
    docId: str | None = None


class InvestigationStage(Model):
    """One specialist node's traceable result and its evidence boundary."""
    key: Literal["scope", "run_comparison", "sensor", "maintenance", "recommendation"]
    title: str
    status: Literal["sample_based", "partial", "unavailable", "provisional"]
    agent_mode: Literal["llm", "rule_based"] = "rule_based"
    historyIds: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    caseIds: list[str] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)


class Report(Model):
    context: Context
    scored: list[Case]
    metrics: list[Metric]
    causeCases: list[Case]
    docIds: list[str]
    documents: list[Document]
    history: list[HistoryEvidence] = Field(default_factory=list)
    checks: list[InvestigationCheck]
    stages: list[InvestigationStage]
    summary: str
    unknowns: list[str]
    feedback: list[str]
    demo: Literal[True] = True


class Clarification(Model):
    text: str = Field(min_length=1)


class Review(Model):
    action: Literal["approve", "revise"]
    comment: str
    by: str = Field(min_length=1)


class InitialRequest(Model):
    question: str = Field(min_length=1)


class ResumeRequest(Model):
    resume: Clarification | Review


class Event(Model):
    event_id: str
    type: EventType
    payload: dict[str, JsonValue]
