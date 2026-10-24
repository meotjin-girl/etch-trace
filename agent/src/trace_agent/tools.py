# Copyright 2026 TRACE contributors
"""The evidence tools exposed to the single ReAct loop."""

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, JsonValue, TypeAdapter

from .evidence import Evidence
from .models import (
    Case,
    Context,
    PhysicsEducationalSimulationInputs,
    PhysicsInputs,
    PhysicsMetrologyComparisonInputs,
    PhysicsQuantitativeInputs,
    PhysicsRateSeriesInputs,
    PhysicsReferenceComparisonInputs,
)


def _physics_arguments(inputs: BaseModel) -> dict[str, JsonValue]:
    """Serialize a typed Agent input using the Physics MCP's nested input shape."""
    return {
        "inputs": TypeAdapter(dict[str, JsonValue]).validate_python(
            inputs.model_dump(mode="json", exclude_none=True)
        )
    }


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
    async def compare_reference_runs(inputs: PhysicsReferenceComparisonInputs) -> JsonValue:
        """실제 제공된 과거 정상 Run만 대상으로 동일 조건 편차를 비교한다.

        Run 이력을 직접 조회하지 않으므로 실제 자료만 입력으로 받는다.
        """
        return await evidence.call(
            "physics", "compare_reference_runs", _physics_arguments(inputs)
        )

    @tool
    async def integrate_etch_rate_series(inputs: PhysicsRateSeriesInputs) -> JsonValue:
        """명시된 실측·가정 식각률 구간만 적분한다.

        센서값만으로 식각률을 만들어내지 않는다.
        """
        return await evidence.call(
            "physics", "integrate_etch_rate_series", _physics_arguments(inputs)
        )

    @tool
    async def compare_metrology_to_spec(inputs: PhysicsMetrologyComparisonInputs) -> JsonValue:
        """실측·목표값과 승인된 같은 단위의 관리한계를 비교한다.

        승인 규격이 없으면 합격·불합격을 판정하지 않는다.
        """
        return await evidence.call(
            "physics", "compare_metrology_to_spec", _physics_arguments(inputs)
        )

    @tool
    async def analyze_etch_quantitatively(inputs: PhysicsQuantitativeInputs) -> JsonValue:
        """제공된 계측·목표·승인한계와 식각률 구간의 v2 정량 분석을 수행한다."""
        return await evidence.call(
            "physics", "analyze_etch_quantitatively", _physics_arguments(inputs)
        )

    @tool
    async def simulate_educational_etch(
        inputs: PhysicsEducationalSimulationInputs,
    ) -> JsonValue:
        """명시적 사용자 요청이 있을 때만 미검증 교육용 가정 모델을 실행한다."""
        return await evidence.call(
            "physics", "simulate_educational_etch", _physics_arguments(inputs)
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
        compare_reference_runs,
        integrate_etch_rate_series,
        compare_metrology_to_spec,
        analyze_etch_quantitatively,
        simulate_educational_etch,
        list_investigations,
    ]
