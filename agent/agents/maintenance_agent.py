"""Independent maintenance-agent graph; maintenance history is not integrated."""

from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build():
    def collect(state: AgentState) -> dict[str, object]:
        # A future maintenance-history MCP response belongs here.
        return {"maintenance_records": []}

    def fallback(state: AgentState) -> InvestigationStage:
        return InvestigationStage(
            key="maintenance", title="정비 이력 확인 에이전트", status="unavailable",
            unknowns=[
                "정비 이력 API/MCP가 연결되지 않아 PM, 부품 교체, Chamber Cleaning, 설정 변경을 조회하지 않았습니다.",
                "정비 시점과 이상 발생의 선후 관계·인과관계를 평가할 근거가 없습니다.",
            ],
        )

    return create_specialist_agent(
        title="정비 이력 확인 에이전트", status="unavailable",
        instructions="정비 기록 도구 응답이 없으면 정비 내역을 추정하지 않습니다. 확인 불가 상태와 필요한 기록 종류만 말하세요.",
        collect=collect, fallback=fallback,
    )
