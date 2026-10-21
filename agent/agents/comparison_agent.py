"""Independent run-comparison agent; calculations remain deterministic MCP output."""

from ..evidence import EvidenceProvider
from ..models import InvestigationStage
from .common import AgentState, create_specialist_agent


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        cases = state.get("cases", [])
        context = state["context"]
        return {"metrics": evidence.analyze_metrics(cases, context)}

    def fallback(state: AgentState) -> InvestigationStage:
        metrics = state.get("metrics", [])
        if not metrics:
            return InvestigationStage(
                key="run_comparison", title="동일 조건 Run 비교 에이전트",
                status="unavailable",
                unknowns=[
                    "입력한 계측값과 일치하는 데모 사례 지표가 없어 정량 비교를 수행하지 못했습니다.",
                    "실제 Recipe/Step별 과거 Run 시계열은 연결되지 않았습니다.",
                ],
            )
        findings = [
            f"{metric.key}: 입력값 {metric.value}, 데모 사례 평균 {metric.mean:.3f}, "
            f"평균 대비 {metric.deltaPct:.2f}%, z-score "
            f"{metric.z if metric.z is not None else '계산 불가'} ({metric.severity})"
            for metric in metrics
        ]
        supporting_ids = list(dict.fromkeys(
            case_id
            for metric in metrics
            for case_id in (
                getattr(metric, "caseIds", None)
                or getattr(metric, "supporting_case_ids", [])
                or []
            )
        ))
        return InvestigationStage(
            key="run_comparison", title="동일 조건 Run 비교 에이전트",
            status="sample_based", findings=findings,
            unknowns=[
                "비교군은 실측 과거 Run이 아니라 Business MCP 데모 사례입니다.",
                "Recipe/Step별 Run 시계열 비교는 아직 연결되지 않았습니다.",
            ],
            caseIds=supporting_ids,
        )

    def status(state: AgentState) -> str:
        return "sample_based" if state.get("metrics") else "unavailable"

    return create_specialist_agent(
        title="동일 조건 Run 비교 에이전트", status=status,
        instructions="도구가 계산한 측정값·평균·편차만 비교합니다. Recipe/Step 실측 Run이 없으면 그 한계를 분명히 하세요.",
        collect=collect, fallback=fallback,
    )
