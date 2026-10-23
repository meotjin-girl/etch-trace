"""Explicit MCP-backed tools exposed to the single ReAct agent."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .evidence import EvidenceProvider
from .models import Context, PhysicsInputs, Requester

TOOL_NAMES = (
    "search_cases",
    "analyze_metrics",
    "search_documents",
    "search_sop",
    "evaluate_etch_physics",
    "list_investigations",
    "record_selection",
)


def build_tools(evidence: EvidenceProvider) -> list[Any]:
    """Create the concrete tool list used by the model and LangGraph ToolNode."""

    @tool
    def search_cases(
        context: dict[str, Any],
        state: Annotated[dict[str, Any], InjectedState],
    ) -> object:
        """Business MCP에서 장비·챔버·recipe·증상·계측 조건과 유사한 사례를 검색한다.

        context에는 equipment, chamber, recipe, symptom, metrics를 넣는다.
        """
        del state
        try:
            return evidence.search_cases(Context.model_validate(context))
        except Exception as error:
            return {"error": f"사례 검색 실패: {type(error).__name__}: {error}"}

    @tool
    def analyze_metrics(
        case_ids: list[str],
        metrics: dict[str, float],
        state: Annotated[dict[str, Any], InjectedState],
    ) -> object:
        """Business MCP로 관측 계측값을 사례 기준 통계와 결정론적으로 비교한다."""
        del state
        try:
            cases = evidence.search_cases(Context())
            selected = [case for case in cases if case.id in set(case_ids)]
            return evidence.analyze_metrics(selected, Context(metrics=metrics))
        except Exception as error:
            return {"error": f"계측 비교 실패: {type(error).__name__}: {error}"}

    @tool
    def search_documents(document_ids: list[str]) -> object:
        """RAG MCP에서 사례가 참조한 문서 ID의 원문을 정확히 조회한다."""
        try:
            return evidence.search_documents(document_ids)
        except Exception as error:
            return {"error": f"문서 ID 조회 실패: {type(error).__name__}: {error}"}

    @tool
    def search_sop(query: str) -> object:
        """RAG MCP에서 조치·원인·OCAP ID와 관련된 SOP/WI 조항을 의미 검색한다."""
        searcher = getattr(evidence, "search_sop", None)
        if not callable(searcher):
            return {"error": "SOP 검색 도구가 EvidenceProvider에 연결되지 않았습니다."}
        try:
            return searcher(query)
        except Exception as error:
            return {"error": f"SOP 검색 실패: {type(error).__name__}: {error}"}

    @tool
    def evaluate_etch_physics(inputs: dict[str, Any]) -> object:
        """Physics MCP에서 D=R*t, R=(pre-post)/t, 선택비 계산을 수행한다.

        입력 key는 etch_rate_nm_min, etch_time_sec, pre_thickness_nm,
        post_thickness_nm, target_etch_rate_nm_min, mask_etch_rate_nm_min이다.
        제공된 수치만 전달하고 빠진 수치를 추측하지 않는다.
        """
        try:
            context = Context(physics=PhysicsInputs.model_validate(inputs))
            return evidence.evaluate_etch_physics(context)
        except Exception as error:
            return {"error": f"Physics MCP 계산 실패: {type(error).__name__}: {error}"}

    @tool
    def list_investigations(
        state: Annotated[dict[str, Any], InjectedState],
    ) -> object:
        """현재 대화 요청자에게 허용된 승인 조사 이력을 조회한다."""
        requester_data = state.get("requester")
        reader = getattr(evidence, "list_investigations", None)
        if not isinstance(requester_data, dict) or not callable(reader):
            return {"error": "요청자 신원 또는 이력 조회 도구가 없습니다."}
        try:
            return reader(Requester.model_validate(requester_data))
        except Exception as error:
            return {"error": f"조사 이력 조회 실패: {type(error).__name__}: {error}"}

    @tool
    def record_selection(
        case_id: str,
        cause: str,
        action: str,
        context: dict[str, Any],
        state: Annotated[dict[str, Any], InjectedState],
    ) -> object:
        """사용자가 승인한 원인-조치 세트를 현재 후보 중에서 검증해 대화 상태에 기록한다."""
        try:
            search_context = Context.model_validate(context)
            candidates = [
                case for case in evidence.search_cases(search_context) if case.cause != "이상 없음"
            ][:5]
        except Exception as error:
            return {"error": f"후보 검증 실패: {type(error).__name__}: {error}"}
        selected = next(
            (
                item
                for item in candidates
                if item.id == case_id and item.cause == cause and item.action == action
            ),
            None,
        )
        if selected is None:
            return {"error": "현재 대화의 상위 다섯 원인-조치 후보와 일치하지 않습니다."}
        requester = state.get("requester")
        return {
            "selected_set": {
                "case_id": selected.id,
                "cause": selected.cause,
                "action": selected.action,
                "requester": requester.get("name", "미제공")
                if isinstance(requester, dict)
                else "미제공",
            }
        }

    # The list is explicit and kept in the same order as TOOL_NAMES above.
    tools = [
        search_cases,
        analyze_metrics,
        search_documents,
        search_sop,
        evaluate_etch_physics,
        list_investigations,
        record_selection,
    ]
    assert tuple(item.name for item in tools) == TOOL_NAMES
    return tools
