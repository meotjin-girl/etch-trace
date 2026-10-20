from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .analytics import analyze_metrics
from .models import (
    AgentState,
    ComparableCase,
    EvidenceLink,
    InvestigationRequest,
    MetricAnalysis,
)
from .report import render_report
from .repository import InvestigationRepository


REQUIRED_FIELDS = {
    "equipment_id": "장비 ID",
    "chamber_id": "챔버 ID",
    "event_time": "이상 발생 시각(ISO 8601 권장)",
    "recipe": "공정 레시피",
    "symptom": "관찰된 이상 현상",
    "metrics": "이상 시점의 계측값(지표명: 숫자)",
}


def validate_request(state: AgentState) -> dict:
    request = InvestigationRequest.model_validate(state.get("request", {}))
    missing = []
    for field in REQUIRED_FIELDS:
        value = getattr(request, field)
        if value is None or value == "" or value == {}:
            missing.append(field)
    return {"request": request.model_dump(), "missing_fields": missing}


def route_after_validation(state: AgentState) -> Literal["clarify", "search_history"]:
    return "clarify" if state.get("missing_fields") else "search_history"


def clarify(state: AgentState) -> dict:
    missing = state["missing_fields"]
    answer = interrupt(
        {
            "type": "clarification_required",
            "message": "조사를 계속하려면 아래 정보가 필요합니다.",
            "missing_fields": [
                {"field": field, "question": f"{REQUIRED_FIELDS[field]}을(를) 알려주세요."}
                for field in missing
            ],
            "answer_format": {field: "value" for field in missing},
        }
    )
    if not isinstance(answer, dict):
        raise ValueError("재질문 응답은 필드와 값을 담은 객체여야 합니다.")
    return {"request": {**state["request"], **answer}}


def search_history(state: AgentState, repository: InvestigationRepository) -> dict:
    request = InvestigationRequest.model_validate(state["request"])
    results = repository.find_comparable(request)
    return {"comparable_cases": [item.model_dump() for item in results]}


def analyze(state: AgentState) -> dict:
    request = InvestigationRequest.model_validate(state["request"])
    cases = [ComparableCase.model_validate(item) for item in state.get("comparable_cases", [])]
    results = analyze_metrics(request, cases)
    return {"analyses": [item.model_dump() for item in results]}


def link_evidence(state: AgentState, repository: InvestigationRepository) -> dict:
    docs = repository.documents()
    cases = [ComparableCase.model_validate(item) for item in state.get("comparable_cases", [])]
    links: list[EvidenceLink] = []
    used: set[str] = set()
    for comparable in cases:
        for ref in comparable.case.document_refs:
            if ref in used or ref not in docs:
                continue
            used.add(ref)
            doc = docs[ref]
            links.append(
                EvidenceLink(
                    evidence_id=ref,
                    source=doc["title"],
                    excerpt=doc["excerpt"],
                    supports=f"사례 {comparable.case.case_id}의 조치 및 판정 기준",
                )
            )
    return {"evidence": [item.model_dump() for item in links]}


def draft_report(state: AgentState) -> dict:
    report = render_report(
        InvestigationRequest.model_validate(state["request"]),
        [ComparableCase.model_validate(item) for item in state.get("comparable_cases", [])],
        [MetricAnalysis.model_validate(item) for item in state.get("analyses", [])],
        [EvidenceLink.model_validate(item) for item in state.get("evidence", [])],
        state.get("review_notes", []),
    )
    return {"report": report, "status": "pending_approval"}


def approval_review(state: AgentState) -> Command:
    decision = interrupt(
        {
            "type": "approval_required",
            "message": "조사 기록을 검토해 승인하거나 수정 의견을 남겨주세요.",
            "report": state["report"],
            "answer_format": {
                "approved": True,
                "reviewer": "name",
                "comment": "optional",
                "edited_report": "optional full report",
            },
        }
    )
    if not isinstance(decision, dict) or "approved" not in decision:
        raise ValueError("승인 응답에는 approved 값이 필요합니다.")
    reviewer = decision.get("reviewer", "미지정 검토자")
    comment = decision.get("comment", "")
    round_no = state.get("review_round", 0) + 1
    note = f"검토 {round_no}: {reviewer} — {'승인' if decision['approved'] else '수정 요청'}"
    if comment:
        note += f" ({comment})"
    notes = [*state.get("review_notes", []), note]
    if decision["approved"]:
        report = decision.get("edited_report") or state["report"]
        report = report.replace(
            "- [ ] 조사 책임자 검토 및 승인",
            "- [x] 조사 책임자 검토 및 승인",
        )
        return Command(
            update={
                "report": report + f"\n- 승인자: {reviewer}\n- 승인 의견: {comment or '없음'}\n",
                "review_round": round_no,
                "review_notes": notes,
                "status": "approved",
            },
            goto=END,
        )
    return Command(
        update={
            "review_round": round_no,
            "review_notes": notes,
            "report": decision.get("edited_report", state["report"]),
            "status": "revision_requested",
        },
        goto="draft_report",
    )


def build_graph(
    repository: InvestigationRepository | None = None,
    checkpointer=None,
):
    repository = repository or InvestigationRepository()
    builder = StateGraph(AgentState)
    builder.add_node("validate_request", validate_request)
    builder.add_node("clarify", clarify)
    builder.add_node("search_history", lambda state: search_history(state, repository))
    builder.add_node("analyze", analyze)
    builder.add_node("link_evidence", lambda state: link_evidence(state, repository))
    builder.add_node("draft_report", draft_report)
    builder.add_node("approval_review", approval_review)
    builder.add_edge(START, "validate_request")
    builder.add_conditional_edges("validate_request", route_after_validation)
    builder.add_edge("clarify", "validate_request")
    builder.add_edge("search_history", "analyze")
    builder.add_edge("analyze", "link_evidence")
    builder.add_edge("link_evidence", "draft_report")
    builder.add_edge("draft_report", "approval_review")
    return builder.compile(checkpointer=checkpointer or InMemorySaver())

