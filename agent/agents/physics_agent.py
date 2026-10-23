"""Deterministic physics stage; the LLM never owns calculated values."""

from ..evidence import EvidenceProvider
from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build(physics: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        return {
            "physics_results": physics.evaluate_etch_physics(state["context"]),
            "quantitative_results": physics.analyze_etch_quantitatively(state["context"]),
            "educational_simulation": physics.simulate_etch_education(
                state["context"], state.get("sensor_analysis"),
            ),
        }

    def fallback(state: AgentState) -> InvestigationStage:
        results = state.get("physics_results", [])
        quantitative = state.get("quantitative_results", [])
        simulation = state.get("educational_simulation")
        calculated = [item for item in results if item.status == "calculated"]
        findings = [
            f"{item.result.key}: {item.result.value:.6g} {item.result.unit} "
            f"({item.formula}; 계산값, 실측값 아님)"
            for item in calculated if item.result is not None
        ]
        unknowns = [
            f"{item.model}: 추가 데이터 필요 ({', '.join(item.missing_fields)})"
            for item in results if item.status == "needs_more_data"
        ] + [
            f"{item.model}: 입력값 오류 ({'; '.join(item.warnings)})"
            for item in results if item.status == "invalid_input"
        ] + [
            f"{item.analysis}: 추가 데이터 필요 ({', '.join(item.missing_fields)})"
            for item in quantitative if item.status == "INSUFFICIENT_DATA"
        ]
        findings.extend(
            f"{item.problem}: " + ", ".join(
                f"{value.key}={value.value:.6g} {value.unit}" for value in item.results
            )
            for item in quantitative if item.status == "CALCULATED"
        )
        if simulation and simulation.status == "SIMULATED":
            final = simulation.profile_frames[-1]
            findings.append(
                "교육용 시뮬레이션(검증되지 않음): "
                f"깊이={final.depth_nm:.6g} nm, AR={final.aspect_ratio:.6g}; "
                "실측·원인 분석 결과가 아님"
            )
        if simulation and simulation.status != "SIMULATED":
            unknowns.append(
                f"교육용 시뮬레이션 {simulation.status}: "
                f"{', '.join(simulation.missing_fields or simulation.warnings)}"
            )
        return InvestigationStage(
            key="physics",
            title="물리 관계식 검증 에이전트",
            status=(
                "partial" if calculated or any(
                    item.status == "CALCULATED" for item in quantitative
                ) or (simulation is not None and simulation.status == "SIMULATED")
                else "unavailable"
            ),
            findings=findings,
            unknowns=unknowns,
        )

    def stage_status(state: AgentState) -> str:
        simulation = state.get("educational_simulation")
        available = (
            any(item.status == "calculated" for item in state.get("physics_results", []))
            or any(
                item.status == "CALCULATED"
                for item in state.get("quantitative_results", [])
            )
            or (simulation is not None and simulation.status == "SIMULATED")
        )
        return "partial" if available else "unavailable"

    return create_specialist_agent(
        title="물리 관계식 검증 에이전트",
        status=stage_status,
        instructions=(
            "Physics MCP의 계산값·입력·가정만 설명하세요. 계산값을 실측값으로 부르거나 "
            "식각 편차만으로 설비 고장, Recipe 변경, Lot release를 결론내리지 마세요."
            " 교육용 시뮬레이션은 실제 조사 근거와 분리하고 검증된 예측이라고 부르지 마세요."
        ),
        collect=collect,
        fallback=fallback,
    )
