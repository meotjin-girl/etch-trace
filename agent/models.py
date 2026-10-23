"""Typed inputs and evidence models used by the single ReAct agent."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PhysicsInputs(Model):
    etch_rate_nm_min: float | None = None
    etch_time_sec: float | None = None
    pre_thickness_nm: float | None = None
    post_thickness_nm: float | None = None
    target_etch_rate_nm_min: float | None = None
    mask_etch_rate_nm_min: float | None = None
    sources: dict[str, str] = Field(default_factory=dict)


class Context(Model):
    equipment: str | None = None
    chamber: str | None = None
    recipe: str | None = None
    symptom: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    physics: PhysicsInputs = Field(default_factory=PhysicsInputs)


class Requester(Model):
    name: str
    role: Literal["user", "worker", "engineer", "admin"]


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
    model_config = ConfigDict(frozen=True, extra="allow")
    key: str
    value: float
    mean: float
    std: float
    deltaPct: float
    z: float | None
    severity: str


class PhysicalValue(Model):
    key: str
    value: float
    unit: str
    source: str


class PhysicsResult(Model):
    model: Literal["etch_depth_constant_rate", "average_etch_rate", "selectivity"]
    version: Literal["1.0"] = "1.0"
    status: Literal["calculated", "needs_more_data", "invalid_input"]
    formula: str
    inputs: list[PhysicalValue] = Field(default_factory=list)
    result: PhysicalValue | None = None
    assumptions: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Document(Model):
    model_config = ConfigDict(frozen=True, extra="allow")
    id: str
    title: str
    text: str


class Clarification(Model):
    text: str = Field(min_length=1)


class Review(Model):
    action: Literal["approve", "revise"]
    comment: str
    by: str = Field(min_length=1)


class InitialRequest(Model):
    """Compatibility with backend versions still posting {question}."""

    question: str = Field(min_length=1)


class AgentMessage(Model):
    role: Literal["system", "user"]
    content: str = Field(min_length=1)


class ResumeRequest(Model):
    """Compatibility envelope; continuation is converted into a user message."""

    resume: Clarification | Review
