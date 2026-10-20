"""Independent recommendation-agent graph grounded in cases and RAG clauses."""

from ..evidence import EvidenceProvider
from ..models import InvestigationStage
from ..provisional_sop import provisional_checks
from .common import AgentState, create_specialist_agent


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        cases = state.get("cases", [])
        context = state["context"]
        candidates = [case for case in cases if case.cause != "이상 없음"][:3]
        ids = list(dict.fromkeys(
            doc_id for case in candidates for doc_id in case.docs
        ))
        return {
            "documents": evidence.search_documents(ids),
            "checks": provisional_checks(context),
        }

    def fallback(state: AgentState) -> InvestigationStage:
        cases = state.get("cases", [])
        documents = state.get("documents", [])
        checks = state.get("checks", [])
        candidates = [case for case in cases if case.cause != "이상 없음"][:3]
        findings = [
            f"데모 후보 {case.id}: {case.cause} — 확인 조치: {case.action}"
            for case in candidates
        ] or ["데모 근거에서 원인 후보를 만들지 못했습니다."]
        unknowns = [
            "후보와 조치는 과거 데모 사례의 가설이며 현재 설비의 확정 원인이 아닙니다.",
            "현장 센서·MES·정비 자료로 후보를 검증해야 합니다.",
        ]
        if not documents:
            unknowns.append("연결 가능한 관련 문서 조항이 없습니다.")
        return InvestigationStage(
            key="recommendation", title="원인 후보·점검 순서 추천 에이전트",
            status="provisional",
            findings=findings + [f"임시 SOP 점검 항목 {len(checks)}개를 별도로 제시했습니다."],
            unknowns=unknowns,
            caseIds=[case.id for case in candidates],
            docIds=[document.id for document in documents],
        )

    return create_specialist_agent(
        title="원인 후보·점검 순서 추천 에이전트",
        status="provisional",
        instructions="사례 원인·조치를 가설로만 제시하고 RAG가 반환한 조항만 문서 근거로 사용합니다. 실제 설비 원인을 확정하지 마세요.",
        collect=collect, fallback=fallback,
    )
