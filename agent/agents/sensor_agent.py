"""Independent sensor-agent graph backed by the read-only Sensor MCP."""

from ..evidence import EvidenceProvider
from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        existing = state.get("sensor_analysis")
        return {
            "sensor_analysis": existing or evidence.analyze_sensor_run(state["context"]),
        }

    def fallback(state: AgentState) -> InvestigationStage:
        analysis = state.get("sensor_analysis")
        if analysis is None or analysis.status != "CALCULATED":
            return InvestigationStage(
                key="sensor", title="센서 교차 확인 에이전트", status="unavailable",
                unknowns=(
                    ["동기화된 센서 시계열을 분석하지 못했습니다."]
                    if analysis is None else [
                        *analysis.warnings,
                        "추가 데이터 필요: " + ", ".join(analysis.missing_fields),
                    ]
                ),
            )
        abnormal = [signal for signal in analysis.signals if signal.first_anomaly_sec is not None]
        findings = [
            f"{signal.sensor}: 최초 이상 {signal.first_anomaly_sec:g}초, "
            f"지속 {signal.anomaly_duration_sec:g}초, 범위 "
            f"{signal.minimum:.6g}~{signal.maximum:.6g} {signal.unit}"
            for signal in abnormal
        ] or ["분석한 센서에서 합성 기준 또는 장비 알람 기준 이상을 찾지 못했습니다."]
        return InvestigationStage(
            key="sensor", title="센서 교차 확인 에이전트", status="partial",
            findings=findings,
            unknowns=[
                *analysis.warnings,
                "동반 이상 시점만으로 인과관계나 특정 부품 고장을 확정하지 않았습니다.",
            ],
        )

    def status(state: AgentState) -> str:
        analysis = state.get("sensor_analysis")
        return "partial" if analysis and analysis.status == "CALCULATED" else "unavailable"

    return create_specialist_agent(
        title="센서 교차 확인 에이전트", status=status,
        instructions=(
            "입력 계측값과 원본 센서 태그·시계열을 구별합니다. 센서 데이터가 비어 "
            "있으면 교차 상관이나 센서 이상을 주장하지 마세요."
        ),
        collect=collect, fallback=fallback,
    )
