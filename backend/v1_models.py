"""Boundary models for the v1 backend and agent protocol."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Role = Literal["user", "worker", "engineer", "admin"]
Status = Literal[
    "QUEUED",
    "RUNNING",
    "WAITING_INPUT",
    "WAITING_APPROVAL",
    "DONE",
    "INCOMPLETE",
    "FAILED",
]


class Input(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class TaskInput(Input):
    question: str = Field(min_length=1, max_length=10000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


class MessageInput(Input):
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ApprovalInput(Input):
    action: Literal["approve", "revise"]
    comment: str = Field(default="", max_length=10000)
    event_time: datetime | None = None
    lot_id: str | None = Field(default=None, max_length=200)


class Document(Input):
    id: str
    title: str
    text: str
    is_demo: bool | None = None
    source: str | None = None
    revision: str | None = None
    notice: str | None = None
    distance: float | None = None


class InvestigationCheck(Input):
    title: str
    rationale: str
    source: Literal["rag_mcp", "provisional_sop"] = "rag_mcp"
    docId: str | None = None


class InvestigationStage(Input):
    key: Literal[
        "scope", "run_comparison", "physics", "sensor", "maintenance", "recommendation",
    ]
    title: str
    status: Literal["sample_based", "partial", "unavailable", "provisional"]
    agent_mode: Literal["llm", "rule_based"] = "rule_based"
    historyIds: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    caseIds: list[str] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)


class HistoryEvidence(Input):
    id: str
    question: str
    summary: str
    causes: list[str] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)
    approvedBy: str
    approvedAt: str
    eventTime: str | None = None
    lotId: str | None = None


class PhysicalValue(Input):
    key: str
    value: float
    unit: str
    source: str


class PhysicsResult(Input):
    model: Literal["etch_depth_constant_rate", "average_etch_rate", "selectivity"]
    version: Literal["1.0"] = "1.0"
    status: Literal["calculated", "needs_more_data", "invalid_input"]
    formula: str
    inputs: list[PhysicalValue] = Field(default_factory=list)
    result: PhysicalValue | None = None
    assumptions: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    problem: str = ""
    interpretation: str = ""
    recommended_checks: list[str] = Field(default_factory=list)


class ControlLimit(Input):
    lower: float | None = None
    upper: float | None = None
    unit: str
    approved: bool = False
    document_id: str | None = None
    revision: str | None = None


class QuantitativeValue(Input):
    key: str
    value: float
    unit: str
    origin: Literal["MEASURED", "CALCULATED", "SIMULATED"]
    source: str


class QuantitativeResult(Input):
    analysis: Literal[
        "reference_run_comparison", "time_resolved_etch_depth", "metrology_comparison",
    ]
    version: Literal["2.0"] = "2.0"
    problem: str
    status: Literal["CALCULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    value_origin: Literal["MEASURED", "CALCULATED", "SIMULATED"] | None = None
    validation_status: Literal["VALIDATED", "NOT_VALIDATED"] = "NOT_VALIDATED"
    formula: str
    inputs: list[QuantitativeValue] = Field(default_factory=list)
    results: list[QuantitativeValue] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    interpretation: str = ""
    recommended_checks: list[str] = Field(default_factory=list)
    within_control_limit: bool | None = None
    control_limit: ControlLimit | None = None


class SensorSignalAnalysis(Input):
    sensor: str
    unit: str
    minimum: float
    maximum: float
    mean: float
    first_anomaly_sec: float | None = None
    anomaly_duration_sec: float = 0
    maximum_setpoint_deviation: float | None = None
    reference_comparison: QuantitativeResult | None = None
    cooccurring_sensors: list[str] = Field(default_factory=list)
    related_alarms: list[str] = Field(default_factory=list)
    ocap_ids: list[str] = Field(default_factory=list)
    threshold_source: Literal["synthetic_baseline", "equipment_alarm", "none"] = "none"


class SensorProcessPoint(Input):
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
    source: str = "mock_fab_sensor"


class SensorAnalysis(Input):
    version: Literal["2.0"] = "2.0"
    problem: str
    status: Literal["CALCULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    target_run_id: str | None = None
    signals: list[SensorSignalAnalysis] = Field(default_factory=list)
    process_series: list[SensorProcessPoint] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    causal_conclusion: Literal[False] = False


class SensitivityCoefficient(Input):
    variable: Literal["source_rf", "bias_rf", "pressure", "sf6", "o2", "esc_temp"]
    value: float
    unit: Literal["per_relative_change"] = "per_relative_change"
    source: str
    calibrated: Literal[False] = False


class RelativeRatePoint(Input):
    offset_sec: float
    relative_rate: float
    simulated_process_rate_nm_min: float
    source: str


class ProfileCoordinate(Input):
    x_nm: float
    y_nm: float


class ProfileFrame(Input):
    offset_sec: float
    depth_nm: float
    opening_width_nm: float
    aspect_ratio: float
    simulated_arde_rate_nm_min: float
    removed_region: list[ProfileCoordinate]


class EducationalSimulationResult(Input):
    version: Literal["3.0"] = "3.0"
    mode: Literal["EDUCATIONAL_ASSUMPTION"] = "EDUCATIONAL_ASSUMPTION"
    status: Literal["SIMULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    validation_status: Literal["NOT_VALIDATED"] = "NOT_VALIDATED"
    completed_levels: list[Literal[1, 2, 3]] = Field(default_factory=list)
    source_run_id: str | None = None
    arde_coefficient: float | None = None
    arde_coefficient_source: str = (
        "TRACE educational assumption v1; not literature-derived or calibrated"
    )
    arde_coefficient_calibrated: Literal[False] = False
    formulas: list[str] = Field(default_factory=list)
    coefficients: list[SensitivityCoefficient] = Field(default_factory=list)
    relative_rate_series: list[RelativeRatePoint] = Field(default_factory=list)
    profile_frames: list[ProfileFrame] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    causal_conclusion: Literal[False] = False


class Report(Input):
    context: dict[str, JsonValue] = Field(default_factory=dict)
    scored: list[dict[str, JsonValue]] = Field(default_factory=list)
    metrics: list[dict[str, JsonValue]] = Field(default_factory=list)
    physicsResults: list[PhysicsResult] = Field(default_factory=list)
    quantitativeResults: list[QuantitativeResult] = Field(default_factory=list)
    sensorAnalysis: SensorAnalysis | None = None
    educationalSimulation: EducationalSimulationResult | None = None
    causeCases: list[dict[str, JsonValue]] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    history: list[HistoryEvidence] = Field(default_factory=list)
    checks: list[InvestigationCheck] = Field(default_factory=list)
    stages: list[InvestigationStage] = Field(default_factory=list)
    summary: str = ""
    unknowns: list[str] = Field(default_factory=list)
    feedback: list[JsonValue] = Field(default_factory=list)
    demo: Literal[True] = True


class Callback(Input):
    type: str = Field(min_length=1, max_length=100)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    event_id: str = Field(min_length=1, max_length=200)


class Output(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


class CaseData(Output):
    data: dict[str, JsonValue]


class Event(Output):
    task_id: UUID
    seq: int
    event_id: str | None
    type: str
    payload: dict[str, JsonValue]
    created_at: datetime


class Message(Output):
    id: int
    task_id: UUID
    role: str
    text: str
    user_name: str
    user_role: str
    user_id: str | None = None
    created_at: datetime


class Review(Output):
    id: int
    task_id: UUID
    action: Literal["approve", "revise"]
    comment: str
    user_name: str
    user_role: Role
    user_id: str | None = None
    report: Report | None
    event_time: datetime | None
    lot_id: str | None
    created_at: datetime


class Investigation(Output):
    id: int
    task_id: UUID
    review_id: int
    report: Report
    approved_by: str
    approved_role: Role
    approved_by_id: str | None = None
    event_time: datetime | None
    lot_id: str | None
    approved_at: datetime
    created_at: datetime


class InvestigationRecord(Output):
    """Approved report and existing storage metadata, without conversation history."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    id: UUID
    user_name: str
    user_role: Role
    user_id: str | None = None
    question: str
    status: Literal["DONE"] = "DONE"
    report: Report
    approved_by: str
    approved_role: Role
    approved_by_id: str | None = None
    event_time: datetime | None
    lot_id: str | None
    approved_at: datetime
    created_at: datetime
    updated_at: datetime


class Task(Output):
    id: UUID
    user_name: str
    user_role: Role
    user_id: str | None = None
    question: str
    command_id: UUID
    status: Status
    report: Report | None
    created_at: datetime
    updated_at: datetime


class Detail(Task):
    messages: list[Message]
    events: list[Event]
    reviews: list[Review]
    investigation: Investigation | None


@dataclass(frozen=True, slots=True)
class Actor:
    name: str
    role: Role
    subject: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class Requester:
    """Stored attribution for trusted dispatch, not a live login session."""

    name: str
    role: Role


# compose mounts sop-ocap/ at SOP_DOCUMENTS_DIR; locally the repository folder is used.
DEFAULT_SOP_DIR = str(Path(__file__).resolve().parent.parent / "sop-ocap")


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    agent_url: str
    internal_api_key: str
    sop_dir: str = DEFAULT_SOP_DIR
    keycloak_url: str = "http://localhost:8080/auth"
    keycloak_realm: str = "trace"
    keycloak_client_id: str = "trace-web"
    keycloak_audience: str = "trace-api"
    keycloak_jwks_url: str = ""
    prometheus_url: str = ""  # empty disables alert intake

    @property
    def issuer(self) -> str:
        return f"{self.keycloak_url.rstrip('/')}/realms/{self.keycloak_realm}"
