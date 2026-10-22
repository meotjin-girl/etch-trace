"""Deterministic physics stage; the LLM never owns calculated values."""

from ..evidence import EvidenceProvider
from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build(physics: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        return {"physics_results": physics.evaluate_etch_physics(state["context"])}

    def fallback(state: AgentState) -> InvestigationStage:
        results = state.get("physics_results", [])
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
        ]
        return InvestigationStage(
            key="physics",
            title="물리 관계식 검증 에이전트",
            status="partial" if calculated else "unavailable",
            findings=findings,
            unknowns=unknowns,
        )

    return create_specialist_agent(
        title="물리 관계식 검증 에이전트",
        status=lambda state: "partial" if any(
            item.status == "calculated" for item in state.get("physics_results", [])
        ) else "unavailable",
        instructions=(
            "Physics MCP의 계산값·입력·가정만 설명하세요. 계산값을 실측값으로 부르거나 "
            "식각 편차만으로 설비 고장, Recipe 변경, Lot release를 결론내리지 마세요."
        ),
        collect=collect,
        fallback=fallback,
    )
