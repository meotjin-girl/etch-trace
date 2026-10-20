from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .answer import render_answer
from .graph import (
    analyze,
    approval_review,
    draft_report,
    link_evidence,
    search_history,
    validate_request,
)
from .models import AgentState, ComparableCase, EvidenceLink, InvestigationRequest, MetricAnalysis
from .query import clarification_message, parse_question, query_missing_fields
from .repository import InvestigationRepository


def understand_question(state: AgentState) -> dict:
    request = parse_question(state["question"], state.get("request"))
    return {
        "request": request.model_dump(),
        "query_missing": query_missing_fields(request),
    }


def route_query(state: AgentState) -> str:
    return "clarify_question" if state.get("query_missing") else "search_history"


def clarify_question(state: AgentState) -> dict:
    reply = interrupt(
        {
            "type": "question_clarification",
            "message": clarification_message(state["query_missing"]),
        }
    )
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("추가 정보를 문장으로 입력해 주세요.")
    return {"question": state["question"] + "\n추가 정보: " + reply.strip()}


def compose_answer(state: AgentState) -> dict:
    answer = render_answer(
        InvestigationRequest.model_validate(state["request"]),
        [ComparableCase.model_validate(item) for item in state.get("comparable_cases", [])],
        [MetricAnalysis.model_validate(item) for item in state.get("analyses", [])],
        [EvidenceLink.model_validate(item) for item in state.get("evidence", [])],
    )
    return {"answer": answer, "status": "answered"}


def offer_report(state: AgentState) -> Command:
    decision = interrupt(
        {
            "type": "record_offer",
            "message": "이 답변을 승인용 조사 기록으로 작성할까요?",
            "answer": state["answer"],
        }
    )
    wants_report = bool(decision.get("create_report")) if isinstance(decision, dict) else bool(decision)
    if wants_report:
        return Command(update={"wants_report": True}, goto="validate_report_request")
    return Command(update={"wants_report": False, "status": "answered"}, goto=END)


def route_report_validation(state: AgentState) -> str:
    return "clarify_report" if state.get("missing_fields") else "search_report_history"


def clarify_report(state: AgentState) -> dict:
    missing = state["missing_fields"]
    labels = {
        "equipment_id": "장비 ID",
        "chamber_id": "챔버 ID",
        "event_time": "이상 발생 시각",
        "recipe": "공정 레시피",
        "symptom": "이상 현상",
        "metrics": "계측값",
    }
    answer = interrupt(
        {
            "type": "record_clarification",
            "message": "승인용 기록을 만들려면 아래 정보가 더 필요합니다.",
            "missing_fields": [
                {"field": field, "question": f"{labels[field]}을(를) 알려주세요."}
                for field in missing
            ],
        }
    )
    if not isinstance(answer, dict):
        raise ValueError("기록 보완 정보는 필드와 값을 담은 객체여야 합니다.")
    return {"request": {**state["request"], **answer}}


def build_chat_graph(
    repository: InvestigationRepository | None = None,
    checkpointer=None,
):
    repository = repository or InvestigationRepository()
    builder = StateGraph(AgentState)
    builder.add_node("understand_question", understand_question)
    builder.add_node("clarify_question", clarify_question)
    builder.add_node("search_history", lambda state: search_history(state, repository))
    builder.add_node("analyze", analyze)
    builder.add_node("link_evidence", lambda state: link_evidence(state, repository))
    builder.add_node("compose_answer", compose_answer)
    builder.add_node("offer_report", offer_report)
    builder.add_node("validate_report_request", validate_request)
    builder.add_node("clarify_report", clarify_report)
    builder.add_node("search_report_history", lambda state: search_history(state, repository))
    builder.add_node("analyze_report", analyze)
    builder.add_node("link_report_evidence", lambda state: link_evidence(state, repository))
    builder.add_node("draft_report", draft_report)
    builder.add_node("approval_review", approval_review)

    builder.add_edge(START, "understand_question")
    builder.add_conditional_edges("understand_question", route_query)
    builder.add_edge("clarify_question", "understand_question")
    builder.add_edge("search_history", "analyze")
    builder.add_edge("analyze", "link_evidence")
    builder.add_edge("link_evidence", "compose_answer")
    builder.add_edge("compose_answer", "offer_report")
    builder.add_conditional_edges("validate_report_request", route_report_validation)
    builder.add_edge("clarify_report", "validate_report_request")
    builder.add_edge("search_report_history", "analyze_report")
    builder.add_edge("analyze_report", "link_report_evidence")
    builder.add_edge("link_report_evidence", "draft_report")
    builder.add_edge("draft_report", "approval_review")
    return builder.compile(checkpointer=checkpointer or InMemorySaver())

