"""Small deterministic evidence provider, not a graph or interrupt mock."""

from dataclasses import dataclass, field
from statistics import mean, pstdev

from agent.models import (
    Case,
    Context,
    Document,
    EducationalSimulationResult,
    Event,
    Metric,
    PhysicsResult,
    QuantitativeResult,
    SensorAnalysis,
)


def sample_cases() -> list[Case]:
    return [
        Case(
            id=f"CASE-{index}", equipment="ETCH-07", chamber="CH-B", recipe="OX-120",
            symptom="endpoint 지연", metrics={"endpoint_sec": value},
            cause=cause, action="문서에 따른 현장 점검", docs=[f"DOC#{index}"], score=score,
        )
        for index, value, cause, score in [
            (1, 94, "폴리머 누적", 0.95),
            (2, 90, "이상 없음", 0.9),
            (3, 92, "RF 접점 열화", 0.85),
            (4, 96, "압력 제어 이상", 0.8),
            (5, 93, "가스 유량 이상", 0.7),
        ]
    ]


@dataclass
class Evidence:
    """Mutable counters expose whether review replay re-fetches evidence."""

    cases: list[Case] = field(default_factory=sample_cases)
    searches: int = 0
    analyses: int = 0
    documents: int = 0

    def search_cases(self, context: Context) -> list[Case]:
        self.searches += 1
        return [case for case in self.cases if
                not context.equipment or case.equipment == context.equipment]

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        self.analyses += 1
        result = []
        for key, value in context.metrics.items():
            values = [case.metrics[key] for case in cases if key in case.metrics]
            if not values:
                continue
            average, std = mean(values), pstdev(values)
            delta = (value - average) / average * 100 if average else 0
            z = (value - average) / std if std else None
            result.append(Metric.model_validate({
                "key": key, "value": value, "mean": average, "std": std,
                "deltaPct": delta, "z": z,
                "severity": "비정상" if abs(z or 0) >= 2 or abs(delta) >= 20 else "정상",
                "unit": "sec", "caseIds": [case.id for case in cases],
            }))
        return result

    def search_documents(self, document_ids: list[str]) -> list[Document]:
        self.documents += 1
        return [
            Document(id=doc, title="샘플 점검 절차", text="현장 확인 후 판단")
            for doc in document_ids
        ]

    def evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]:
        rate, seconds = context.physics.etch_rate_nm_min, context.physics.etch_time_sec
        missing = [
            key for key, value in (("etch_rate_nm_min", rate), ("etch_time_sec", seconds))
            if value is None
        ]
        result = None
        if not missing:
            assert rate is not None and seconds is not None
            result = {
                "key": "expected_etch_depth_nm", "value": rate * seconds / 60,
                "unit": "nm", "source": "calculated",
            }
        return [PhysicsResult.model_validate({
            "model": "etch_depth_constant_rate", "status": (
                "needs_more_data" if missing else "calculated"
            ),
            "formula": "D = R * t", "result": result, "missing_fields": missing,
        })]

    def analyze_etch_quantitatively(self, context: Context) -> list[QuantitativeResult]:
        measured = context.physics.measured_etch_depth_nm
        target = context.physics.target_etch_depth_nm
        limit = context.physics.depth_control_limit
        if measured is None or target is None or limit is None or not limit.approved:
            return []
        return [QuantitativeResult.model_validate({
            "analysis": "metrology_comparison",
            "problem": "실측 깊이와 승인 규격 비교",
            "status": "CALCULATED",
            "value_origin": "CALCULATED",
            "validation_status": "VALIDATED",
            "formula": "error = measured - target",
            "results": [{
                "key": "absolute_error", "value": measured - target,
                "unit": "nm", "origin": "CALCULATED", "source": "test",
            }],
            "within_control_limit": (
                (limit.lower is None or measured >= limit.lower)
                and (limit.upper is None or measured <= limit.upper)
            ),
            "control_limit": limit,
        })]

    def analyze_sensor_run(self, context: Context) -> SensorAnalysis:
        return SensorAnalysis(
            problem="센서 시계열 정량 분석", status="INSUFFICIENT_DATA",
            missing_fields=["sensor_history"],
        )

    def simulate_etch_education(
        self, context: Context, sensor: SensorAnalysis | None,
    ) -> EducationalSimulationResult | None:
        return None


@dataclass
class Events:
    values: list[Event] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)

    def __call__(self, task_id: str, event: Event) -> None:
        self.values.append(event)
        self.task_ids.append(task_id)
