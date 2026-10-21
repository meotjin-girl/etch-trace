"""Independent sensor-agent graph; no sensor MCP is connected yet."""

from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build():
    def collect(state: AgentState) -> dict[str, object]:
        # This is deliberately empty until an authorized sensor-data MCP exists.
        return {"sensor_data": []}

    def fallback(state: AgentState) -> InvestigationStage:
        context = state["context"]
        if not context.metrics:
            return InvestigationStage(
                key="sensor", title="센서 교차 확인 에이전트", status="unavailable",
                unknowns=["사용자가 입력한 계측값과 동기화된 센서 시계열이 제공되지 않았습니다."],
            )
        readings = [f"{key}={value:g}" for key, value in context.metrics.items()]
        return InvestigationStage(
            key="sensor", title="센서 교차 확인 에이전트", status="partial",
            findings=["사용자 질문에 포함된 계측값: " + ", ".join(readings)],
            unknowns=[
                "값에 장비 원본 태그, 수집 시각, Run/Step 구간 정보가 연결되지 않았습니다.",
                "Gas Flow, 펌프, 밸브 및 독립 압력 센서 간 상관은 확인하지 못했습니다.",
            ],
        )

    def status(state: AgentState) -> str:
        return "partial" if state["context"].metrics else "unavailable"

    return create_specialist_agent(
        title="센서 교차 확인 에이전트", status=status,
        instructions="입력 계측값과 원본 센서 태그·시계열을 구별합니다. 센서 데이터가 비어 있으면 교차 상관이나 센서 이상을 주장하지 마세요.",
        collect=collect, fallback=fallback,
    )
