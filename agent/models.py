"""Wire models shared by the agent's parser, graph, and HTTP boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

type EventType = Literal[
    "SEARCH_STARTED",
    "ANALYSIS_STARTED",
    "REPORT_STARTED",
    "QUESTION",
    "APPROVAL_REQUIRED",
    "DONE",
    "INCOMPLETE",
    "FAILED",
]


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ControlLimit(Model):
    lower: float | None = None
    upper: float | None = None
    unit: str
    approved: bool = False
    document_id: str | None = None
    revision: str | None = None


class RateInterval(Model):
    start_sec: float
    end_sec: float
    etch_rate_nm_min: float
    origin: Literal["MEASURED", "SIMULATED"]
    source: str


class PhysicsInputs(Model):
    etch_rate_nm_min: float | None = None
    etch_time_sec: float | None = None
    pre_thickness_nm: float | None = None
    post_thickness_nm: float | None = None
    target_etch_rate_nm_min: float | None = None
    mask_etch_rate_nm_min: float | None = None
    measured_etch_depth_nm: float | None = None
    target_etch_depth_nm: float | None = None
    depth_control_limit: ControlLimit | None = None
    rate_intervals: list[RateInterval] = Field(default_factory=list)
    simulation_requested: bool = False
    feature_width_nm: float | None = None
    arde_coefficient: float = 0.10
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
    problem: str = ""
    interpretation: str = ""
    recommended_checks: list[str] = Field(default_factory=list)


class QuantitativeValue(Model):
    key: str
    value: float
    unit: str
    origin: Literal["MEASURED", "CALCULATED", "SIMULATED"]
    source: str


class QuantitativeResult(Model):
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


class SensorSignalAnalysis(Model):
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


class SensorProcessPoint(Model):
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


class SensorAnalysis(Model):
    version: Literal["2.0"] = "2.0"
    problem: str
    status: Literal["CALCULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    target_run_id: str | None = None
    signals: list[SensorSignalAnalysis] = Field(default_factory=list)
    process_series: list[SensorProcessPoint] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    causal_conclusion: Literal[False] = False


class SensitivityCoefficient(Model):
    variable: Literal["source_rf", "bias_rf", "pressure", "sf6", "o2", "esc_temp"]
    value: float
    unit: Literal["per_relative_change"] = "per_relative_change"
    source: str
    calibrated: Literal[False] = False


class RelativeRatePoint(Model):
    offset_sec: float
    relative_rate: float
    simulated_process_rate_nm_min: float
    source: str


class ProfileCoordinate(Model):
    x_nm: float
    y_nm: float


class ProfileFrame(Model):
    offset_sec: float
    depth_nm: float
    opening_width_nm: float
    aspect_ratio: float
    simulated_arde_rate_nm_min: float
    removed_region: list[ProfileCoordinate]


class EducationalSimulationResult(Model):
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


class Report(Model):
    context: Context
    scored: list[Case]
    metrics: list[Metric]
    physicsResults: list[PhysicsResult] = Field(default_factory=list)
    quantitativeResults: list[QuantitativeResult] = Field(default_factory=list)
    sensorAnalysis: SensorAnalysis | None = None
    educationalSimulation: EducationalSimulationResult | None = None
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
