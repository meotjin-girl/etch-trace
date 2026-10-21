"""Independent recommendation-agent graph using exact-ID and SOP RAG tools."""

from typing import cast

from ..evidence import EvidenceProvider, SopRagSearcher
from ..models import Document, InvestigationCheck, InvestigationStage
from .common import AgentState, create_specialist_agent


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        cases = state.get("cases", [])
        context = state["context"]
        candidates = [case for case in cases if case.cause != "이상 없음"][:3]
        ids = list(dict.fromkeys(
            doc_id for case in candidates for doc_id in case.docs
        ))
        exact_documents = evidence.search_documents(ids)
        sop_search_error: str | None = None
        sop_documents: list[Document] = []
        search_sop = getattr(evidence, "search_sop", None)
        if callable(search_sop):
            try:
                query = " ".join([
                    value for value in (
                        context.equipment, context.chamber, context.recipe, context.symptom,
                        *(f"{key}={value:g}" for key, value in context.metrics.items()),
                    ) if value
                ])
                sop_documents = cast(SopRagSearcher, evidence).search_sop(query)
            except Exception as error:
                sop_search_error = f"SOP RAG MCP 조회 실패 ({type(error).__name__})"
        else:
            sop_search_error = "SOP RAG MCP 도구가 EvidenceProvider에 연결되지 않았습니다"

        # Prefer the semantically retrieved clause when both MCPs return the same ID.
        documents_by_id = {document.id: document for document in exact_documents}
        documents_by_id.update({document.id: document for document in sop_documents})
        checks = [
            InvestigationCheck(
                title=document.title,
                rationale=document.text[:500].strip() + ("…" if len(document.text) > 500 else ""),
                docId=document.id,
            )
            for document in sop_documents
        ]
        return {
            "documents": list(documents_by_id.values()),
            "checks": checks,
            "sop_search_error": sop_search_error,
        }

    def fallback(state: AgentState) -> InvestigationStage:
        cases = state.get("cases", [])
        documents = state.get("documents", [])
        checks = state.get("checks", [])
        sop_search_error = state.get("sop_search_error")
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
        if sop_search_error:
            unknowns.append(
                f"{sop_search_error}; 의미 기반 SOP 검색 결과는 제공되지 않았습니다."
            )
            sop_finding = (
                "SOP 의미 검색 결과가 없으므로 점검 순서를 제안하지 않았습니다."
            )
        else:
            sop_finding = (
                f"SOP RAG MCP가 반환한 점검 조항 {len(checks)}개를 "
                "관련도 순서로 표시했습니다."
            )
        return InvestigationStage(
            key="recommendation", title="원인 후보·점검 순서 추천 에이전트",
            status="provisional",
            findings=findings + [sop_finding],
            unknowns=unknowns,
            caseIds=[case.id for case in candidates],
            docIds=[document.id for document in documents],
        )

    return create_specialist_agent(
        title="원인 후보·점검 순서 추천 에이전트",
        status="provisional",
        instructions=(
            "사례 원인·조치를 가설로만 제시합니다. SOP 점검 순서와 문서 근거는 "
            "search_sop 또는 search_documents MCP가 실제 반환한 조항만 사용하고, "
            "해당 자료가 없으면 없다고 밝힙니다. 실제 설비 원인을 확정하지 마세요."
        ),
        collect=collect, fallback=fallback,
    )
