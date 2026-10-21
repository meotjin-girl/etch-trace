"""Independent scope-agent graph backed by the existing Business MCP cases."""

from ..evidence import EvidenceProvider
from ..models import Context, InvestigationStage
from .common import AgentState, create_specialist_agent


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        context = state["context"]
        return {"cases": evidence.search_cases(context)}

    def fallback(state: AgentState) -> InvestigationStage:
        context = state["context"]
        cases = state.get("cases", [])
        fields = [
            f"{label}={value}"
            for label, value in (
                ("장비", context.equipment), ("Chamber", context.chamber),
                ("Recipe", context.recipe), ("이상 현상", context.symptom),
            )
            if value
        ]
        return InvestigationStage(
            key="scope", title="범위 조사 에이전트", status="sample_based",
            findings=[
                "질문에서 추출한 범위: " + (", ".join(fields) or "미제공"),
                f"Business MCP 데모 유사 사례 {len(cases)}건을 확인했습니다.",
            ],
            unknowns=[
                "실제 MES Lot/Wafer, 발생 시각, Run 순서, 같은 기간의 타 Lot 사용 이력은 아직 연결되지 않았습니다."
            ],
            caseIds=[case.id for case in cases],
        )

    return create_specialist_agent(
        title="범위 조사 에이전트", status="sample_based",
        instructions="질문 범위와 Business MCP 유사 사례의 공통점만 정리합니다. 실제 MES 조회로 오해하지 않게 하세요.",
        collect=collect, fallback=fallback,
    )
