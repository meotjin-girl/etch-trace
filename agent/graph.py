"""Checkpointed investigation workflow with replay-safe interrupt boundaries."""

from collections.abc import Callable
from typing import Literal, TypedDict
from uuid import UUID, uuid5

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import JsonValue

from .agents import (
    comparison_agent as comparison_agent_module,
    maintenance_agent as maintenance_agent_module,
    recommendation_agent as recommendation_agent_module,
    scope_agent as scope_agent_module,
    sensor_agent as sensor_agent_module,
)
from .evidence import EvidenceProvider
from .models import (
    Case, Clarification, Context, Document, Event, EventType, InvestigationCheck,
    InvestigationStage, Metric, Report, Review,
)
from .query import clarification_message, missing_fields, parse_question


class State(TypedDict):
    task_id: str
    question: str
    context: Context
    clarifications: int
    scored: list[Case]
    metrics: list[Metric]
    documents: list[Document]
    checks: list[InvestigationCheck]
    stages: list[InvestigationStage]
    feedback: list[str]
    report: Report
    review: Review
    reason: str


class TaskInput(TypedDict):
    task_id: str
    question: str


class Update(TypedDict, total=False):
    context: Context
    clarifications: int
    scored: list[Case]
    metrics: list[Metric]
    documents: list[Document]
    checks: list[InvestigationCheck]
    stages: list[InvestigationStage]
    feedback: list[str]
    report: Report
    review: Review
    reason: str


type Emit = Callable[[str, Event], None]


def document_ids(cases: list[Case]) -> list[str]:
    """Use the frontend's first three non-normal hypotheses in scored order."""
    return list(dict.fromkeys(doc for case in cause_cases(cases) for doc in case.docs))


def cause_cases(cases: list[Case]) -> list[Case]:
    return [case for case in cases if case.cause != "이상 없음"][:3]


def template_report(state: State) -> Report:
    """Preserve evidence verbatim and visibly record requested revisions."""
    feedback = state.get("feedback", [])
    summary = (
        f"관련 과거 사례 {len(state['scored'])}건을 비교했습니다. "
        "과거 사례의 원인·조치는 우선 확인 가설이며 현재 공정의 원인으로 확정할 수 없습니다. "
        "현장 점검과 문서 조항 확인이 필요합니다. 단계별 에이전트 결과를 확인하세요."
    )
    if feedback:
        summary += (
            " 검토자의 수정 요청을 feedback에 기록했습니다."
            " 자동 문구 수정은 수행하지 않았습니다."
        )
    available = {document.id for document in state["documents"]}
    missing = [doc for doc in document_ids(state["scored"]) if doc not in available]
    unknowns = ["샘플 사례 기반 분석입니다.", "실제 원인과 조치의 적합성은 현장 확인이 필요합니다."]
    if not state["context"].metrics:
        unknowns.append("현재 계측값이 제공되지 않아 수치 비교를 수행하지 않았습니다.")
    if missing:
        unknowns.append("검색되지 않은 문서 조항: " + ", ".join(missing))
    return Report(
        context=state["context"],
        scored=state["scored"],
        metrics=state["metrics"],
        causeCases=cause_cases(state["scored"]),
        docIds=document_ids(state["scored"]),
        documents=state["documents"],
        checks=state["checks"],
        stages=state["stages"],
        summary=summary,
        unknowns=list(dict.fromkeys([
            *unknowns,
            *(item for stage in state["stages"] for item in stage.unknowns),
        ])),
        feedback=feedback,
    )


def build_graph(checkpointer: BaseCheckpointSaver, evidence: EvidenceProvider, emit: Emit):
    """Compile a graph whose interrupt nodes have no callback side effects."""
    scope_graph = scope_agent_module.build(evidence)
    comparison_graph = comparison_agent_module.build(evidence)
    sensor_graph = sensor_agent_module.build()
    maintenance_graph = maintenance_agent_module.build()
    recommendation_graph = recommendation_agent_module.build(evidence)

    def publish(state: State, kind: EventType,
                payload: dict[str, JsonValue]) -> None:
        # Replayed event nodes produce the same ID; each revision/question differs.
        command_id = get_config().get("configurable", {}).get("command_id", "")
        version = (
            f"{command_id}:{state.get('clarifications', 0)}:"
            f"{len(state.get('feedback', []))}"
        )
        event_id = str(uuid5(UUID(state["task_id"]), f"{kind}:{version}"))
        emit(state["task_id"], Event(event_id=event_id, type=kind, payload=payload))

    def intake(state: State) -> Update:
        return {
            "context": parse_question(state["question"]),
            "clarifications": 0,
            "feedback": [],
            "stages": [],
        }

    def after_intake(state: State) -> Literal["question_event", "search_started", "incomplete"]:
        if not missing_fields(state["context"]):
            return "search_started"
        if state["clarifications"] >= 3:
            return "incomplete"
        return "question_event"

    def question_event(state: State) -> Update:
        missing = missing_fields(state["context"])
        publish(state, "QUESTION", {
            "text": clarification_message(missing), "missing": [field for field in missing],
        })
        return {}

    def clarify(state: State) -> Update:
        missing = missing_fields(state["context"])
        answer = Clarification.model_validate(interrupt({
            "kind": "clarification", "text": clarification_message(missing), "missing": missing,
        }))
        return {
            "context": parse_question(answer.text, state["context"]),
            "clarifications": state["clarifications"] + 1,
        }

    def search_started(state: State) -> Update:
        publish(state, "SEARCH_STARTED", {})
        return {}

    def scope_agent(state: State) -> Update:
        result = scope_graph.invoke({"context": state["context"]})
        return {
            "scored": result.get("cases", []),
            "stages": [*state.get("stages", []), result["result"]],
        }

    def after_scope(state: State) -> Literal["analysis_started", "incomplete"]:
        return "analysis_started" if state["scored"] else "incomplete"

    def analysis_started(state: State) -> Update:
        publish(state, "ANALYSIS_STARTED", {})
        return {}

    def analyze(state: State) -> Update:
        result = comparison_graph.invoke({
            "context": state["context"], "cases": state["scored"],
        })
        return {
            "metrics": result.get("metrics", []),
            "stages": [*state.get("stages", []), result["result"]],
        }

    def sensor_agent(state: State) -> Update:
        result = sensor_graph.invoke({"context": state["context"]})
        return {"stages": [*state.get("stages", []), result["result"]]}

    def maintenance_agent(state: State) -> Update:
        result = maintenance_graph.invoke({"context": state["context"]})
        return {"stages": [*state.get("stages", []), result["result"]]}

    def recommendation_agent(state: State) -> Update:
        result = recommendation_graph.invoke({
            "context": state["context"], "cases": state["scored"],
            "metrics": state["metrics"], "stages": state["stages"],
        })
        return {
            "documents": result.get("documents", []),
            "checks": result.get("checks", []),
            "stages": [*state.get("stages", []), result["result"]],
        }

    def report_started(state: State) -> Update:
        publish(state, "REPORT_STARTED", {})
        return {}

    def report(state: State) -> Update:
        return {"report": template_report(state)}

    def approval_event(state: State) -> Update:
        publish(state, "APPROVAL_REQUIRED", {"report": state["report"].model_dump(mode="json")})
        return {}

    def review(state: State) -> Update:
        decision = Review.model_validate(interrupt({
            "kind": "review", "report": state["report"].model_dump(mode="json"),
        }))
        return {"review": decision}

    def after_review(state: State) -> Literal["done", "feedback"]:
        return "done" if state["review"].action == "approve" else "feedback"

    def feedback(state: State) -> Update:
        comment = state["review"].comment.strip() or "표현과 근거를 다시 검토해 주세요."
        return {"feedback": [*state.get("feedback", []), comment]}

    def done(state: State) -> Update:
        publish(state, "DONE", {
            "report": state["report"].model_dump(mode="json"),
            "approved": True,
            "by": state["review"].by,
        })
        return {}

    def incomplete(state: State) -> Update:
        reason = "추가 질문 3회 후에도 조사 범위 또는 이상 현상이 부족합니다."
        if not missing_fields(state["context"]):
            reason = "조건에 맞는 과거 사례가 없어 근거 기반 보고서를 작성할 수 없습니다."
        publish(state, "INCOMPLETE", {"reason": reason})
        return {"reason": reason}

    builder = StateGraph(State, input_schema=TaskInput)
    nodes = {
        "intake": intake, "question_event": question_event, "clarify": clarify,
        "search_started": search_started,
        "scope_agent": scope_agent,
        "analysis_started": analysis_started, "analyze": analyze,
        "sensor_agent": sensor_agent, "maintenance_agent": maintenance_agent,
        "recommendation_agent": recommendation_agent,
        "report_started": report_started, "report": report,
        "approval_event": approval_event, "review": review,
        "feedback": feedback, "done": done, "incomplete": incomplete,
    }
    for name, node in nodes.items():
        builder.add_node(name, node)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", after_intake)
    builder.add_edge("question_event", "clarify")
    builder.add_conditional_edges("clarify", after_intake)
    builder.add_edge("search_started", "scope_agent")
    builder.add_conditional_edges("scope_agent", after_scope)
    builder.add_edge("analysis_started", "analyze")
    builder.add_edge("analyze", "sensor_agent")
    builder.add_edge("sensor_agent", "maintenance_agent")
    builder.add_edge("maintenance_agent", "recommendation_agent")
    builder.add_edge("recommendation_agent", "report_started")
    builder.add_edge("report_started", "report")
    builder.add_edge("report", "approval_event")
    builder.add_edge("approval_event", "review")
    builder.add_conditional_edges("review", after_review)
    builder.add_edge("feedback", "report_started")
    builder.add_edge("done", END)
    builder.add_edge("incomplete", END)
    return builder.compile(checkpointer=checkpointer)
