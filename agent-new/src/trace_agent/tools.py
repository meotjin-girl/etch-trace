# Copyright 2026 TRACE contributors
"""The six evidence tools exposed to the single ReAct loop."""

from langchain_core.tools import BaseTool, tool
from pydantic import JsonValue, TypeAdapter

from .evidence import Evidence
from .models import Case, Context, PhysicsInputs


def build_tools(evidence: Evidence) -> list[BaseTool]:
    """Bind only evidence access, never publication or approval, to the model."""

    @tool
    async def search_cases(context: Context) -> JsonValue:
        """Search Business MCP for 장비·챔버·recipe·증상·계측 조건과 유사한 사례."""
        return await evidence.call(
            "business",
            "search_cases",
            {
                "context": TypeAdapter(dict[str, JsonValue]).validate_python(
                    context.model_dump(exclude_none=True)
                )
            },
        )

    @tool
    async def analyze_metrics(case_ids: list[str], metrics: dict[str, float]) -> JsonValue:
        """Compare 관측 계측값 with 선택한 사례 기준 통계 using Business MCP."""
        result = await evidence.call("business", "search_cases", {"context": {}})
        cases = TypeAdapter(list[Case]).validate_python(result)
        selected = [case.model_dump(mode="json") for case in cases if case.id in case_ids]
        return await evidence.call(
            "business",
            "analyze_metrics",
            TypeAdapter(dict[str, JsonValue]).validate_python(
                {"cases": selected, "metrics": metrics}
            ),
        )

    @tool
    async def search_documents(document_ids: list[str]) -> JsonValue:
        """RAG MCP에서 사례가 참조한 문서 ID의 원문을 정확히 조회한다."""
        return await evidence.call(
            "rag", "search_documents", {"document_ids": list[JsonValue](document_ids)}
        )

    @tool
    async def search_sop(query: str) -> JsonValue:
        """RAG MCP에서 조치·원인·OCAP ID와 관련된 SOP/WI 조항을 의미 검색한다."""
        return await evidence.call("rag", "search_sop", {"query": query})

    @tool
    async def evaluate_etch_physics(inputs: PhysicsInputs) -> JsonValue:
        """Physics MCP에서 D=R*t, R=(pre-post)/t, 선택비를 계산한다. 수치를 추측하지 않는다."""
        return await evidence.call(
            "physics",
            "evaluate_etch_physics",
            {
                "inputs": TypeAdapter(dict[str, JsonValue]).validate_python(
                    inputs.model_dump(exclude_none=True)
                )
            },
        )

    @tool
    async def list_investigations() -> JsonValue:
        """공동 검토를 위한 승인 조사 이력을 조회한다. 소유자 필터를 적용하지 않는다."""
        # Existing Business MCP requires these legacy attribution arguments.
        return await evidence.call(
            "business",
            "list_investigations",
            {"user_name": "trace-agent", "user_role": "user"},
        )

    return [
        search_cases,
        analyze_metrics,
        search_documents,
        search_sop,
        evaluate_etch_physics,
        list_investigations,
    ]
