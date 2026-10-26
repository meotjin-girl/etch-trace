# Copyright 2026 TRACE contributors
"""The evidence tools exposed to the single ReAct loop."""

import hashlib
import json
from itertools import pairwise

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, JsonValue, TypeAdapter

from .evidence import Evidence
from .models import (
    Case,
    Context,
    MockFabEducationalSimulationInputs,
    PhysicsEducationalSimulationInputs,
    PhysicsEducationalSimulationResult,
    PhysicsInputs,
    PhysicsMetrologyComparisonInputs,
    PhysicsQuantitativeInputs,
    PhysicsRateSeriesInputs,
    PhysicsReferenceComparisonInputs,
    SensorAnalysisResult,
    SensorRunQuery,
)


def _physics_arguments(inputs: BaseModel) -> dict[str, JsonValue]:
    """Serialize a typed Agent input using the Physics MCP's nested input shape."""
    return {
        "inputs": TypeAdapter(dict[str, JsonValue]).validate_python(
            inputs.model_dump(mode="json", exclude_none=True)
        )
    }


def build_tools(evidence: Evidence) -> list[BaseTool]:  # noqa: C901, PLR0915
    """Bind only evidence access, never publication or approval, to the model."""

    async def read_mock_fab_run(
        inputs: SensorRunQuery, *, require_completed: bool,
    ) -> SensorAnalysisResult:
        result = await evidence.call("sensor", "analyze_current_etch_run", {
            **TypeAdapter(dict[str, JsonValue]).validate_python(
                inputs.model_dump(mode="json", exclude_none=True)
            ),
            "require_completed": require_completed,
        })
        return SensorAnalysisResult.model_validate(result)

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
    async def analyze_mock_fab_run(inputs: SensorRunQuery) -> JsonValue:
        """Mock Fab에서 요청 식별자와 정확히 일치하는 Run의 센서 시계열을 조회한다.

        Lot/Wafer 식별 불가 또는 불일치 시 다른 Run을 대입하지 않는다. 센서 결과는
        측정된 합성 데이터이며 식각률이나 특정 부품 고장의 인과 증거가 아니다.
        """
        result = await read_mock_fab_run(inputs, require_completed=False)
        return TypeAdapter(JsonValue).validate_python(result.model_dump(mode="json"))

    @tool
    async def simulate_mock_fab_etch(
        inputs: MockFabEducationalSimulationInputs,
    ) -> JsonValue:
        """명시적 교육용 요청에만 완료된 Mock Fab Run을 조회해 Level 1~3을 계산한다.

        한 번 조회한 동일 process_series를 모든 패턴 폭에 재사용한다. 반환된 snapshot_id,
        target_run_id를 후속 호출의 expected_snapshot_id, target_run_id로 전달하면 입력이
        달라졌을 때 계산을 거부한다. 결과는 항상 SIMULATED/NOT_VALIDATED 교육용 가정이다.
        """
        sensor_query = SensorRunQuery.model_validate(inputs.model_dump(
            include={
                "equipment", "chamber", "lot_id", "wafer_id", "recipe", "step",
                "target_run_id",
            },
        ))
        sensor = await read_mock_fab_run(sensor_query, require_completed=True)
        common: dict[str, JsonValue] = {
            "version": "1.0",
            "mode": "EDUCATIONAL_ASSUMPTION",
            "validation_status": "NOT_VALIDATED",
            "target_identity": TypeAdapter(dict[str, JsonValue]).validate_python({
                "equipment": inputs.equipment,
                "chamber": inputs.chamber,
                "lot_id": inputs.lot_id,
                "wafer_id": inputs.wafer_id,
                "recipe": inputs.recipe,
                "step": inputs.step,
            }),
            "sensor_analysis": TypeAdapter(JsonValue).validate_python(
                sensor.model_dump(mode="json")
            ),
            "snapshot_id": sensor.snapshot_id,
            "target_run_id": sensor.target_run_id,
            "simulations": [],
            "comparisons": [],
            "causal_conclusion": False,
        }
        if sensor.status != "CALCULATED":
            return TypeAdapter(JsonValue).validate_python({
                **common,
                "status": sensor.status,
                "missing_fields": sensor.missing_fields,
                "warnings": sensor.warnings,
            })
        if (
            sensor.equipment != inputs.equipment
            or sensor.chamber != inputs.chamber
            or sensor.lot_id != inputs.lot_id
            or sensor.wafer_id != inputs.wafer_id
            or sensor.recipe != inputs.recipe
            or (inputs.step is not None and sensor.step != inputs.step)
        ):
            return TypeAdapter(JsonValue).validate_python({
                **common,
                "status": "INSUFFICIENT_DATA",
                "missing_fields": ["matching_target_run"],
                "warnings": ["조회된 Run 식별자가 요청 범위와 일치하지 않아 계산을 보류했습니다."],
            })
        if (
            inputs.expected_snapshot_id is not None
            and sensor.snapshot_id != inputs.expected_snapshot_id
        ):
            return TypeAdapter(JsonValue).validate_python({
                **common,
                "status": "INSUFFICIENT_DATA",
                "missing_fields": ["matching_sensor_snapshot"],
                "warnings": ["센서 스냅샷 해시가 이전 계산과 달라 동일 조건 비교를 보류했습니다."],
            })

        points = sensor.process_series
        offsets = [item.offset_sec for item in points]
        intervals = [right - left for left, right in pairwise(offsets)]
        conditions = TypeAdapter(dict[str, JsonValue]).validate_python({
            "initial_depth_nm": 0.0,
            "integration_method": "left-interval rate with adjacent offset_sec delta_t / 60",
            "snapshot_start_offset_sec": sensor.snapshot_start_offset_sec,
            "snapshot_end_offset_sec": sensor.snapshot_end_offset_sec,
            "intervals_sec": intervals,
            "base_etch_rate_nm_min": inputs.base_etch_rate_nm_min,
            "arde_coefficient": inputs.arde_coefficient,
            "arde_coefficient_source": "user_input; uncalibrated educational assumption",
            "units": {
                "source_rf": "W", "bias_rf": "W", "pressure": "mTorr",
                "sf6": "sccm", "o2": "sccm", "esc_temp": "degC",
                "etch_rate": "nm/min", "depth": "nm", "feature_width": "nm",
                "offset_and_delta_t": "s", "relative_rate_and_aspect_ratio": "dimensionless",
                "sensitivity_coefficient": "per_relative_change",
            },
        })
        simulations: list[dict[str, JsonValue]] = []
        parsed_results: list[PhysicsEducationalSimulationResult] = []
        for width in inputs.feature_widths_nm:
            calculation_payload = {
                "snapshot_id": sensor.snapshot_id,
                "target_run_id": sensor.target_run_id,
                "base_etch_rate_nm_min": inputs.base_etch_rate_nm_min,
                "feature_width_nm": width,
                "arde_coefficient": inputs.arde_coefficient,
            }
            calculation_input_id = "sha256:" + hashlib.sha256(
                json.dumps(
                    calculation_payload, sort_keys=True, separators=(",", ":"),
                ).encode()
            ).hexdigest()
            raw_result = await evidence.call(
                "physics", "simulate_educational_etch", {"inputs": {
                    "base_etch_rate_nm_min": inputs.base_etch_rate_nm_min,
                    "feature_width_nm": width,
                    "arde_coefficient": inputs.arde_coefficient,
                    "arde_coefficient_source": (
                        "user_input; uncalibrated educational assumption"
                    ),
                    "process_points": [item.model_dump(mode="json") for item in points],
                    "source_run_id": sensor.target_run_id,
                }},
            )
            result = PhysicsEducationalSimulationResult.model_validate(raw_result)
            parsed_results.append(result)
            final = result.profile_frames[-1] if result.profile_frames else None
            simulations.append(TypeAdapter(dict[str, JsonValue]).validate_python({
                "feature_width_nm": width,
                "calculation_input_id": calculation_input_id,
                "result": result.model_dump(mode="json"),
                "final": (
                    {
                        "offset_sec": final.offset_sec,
                        "depth_nm": final.depth_nm,
                        "aspect_ratio": final.aspect_ratio,
                        "simulated_arde_rate_nm_min": final.simulated_arde_rate_nm_min,
                    }
                    if final is not None else None
                ),
            }))

        comparisons: list[dict[str, JsonValue]] = []
        minimum_comparison_results = 2
        if len(parsed_results) >= minimum_comparison_results:
            baseline = parsed_results[0]
            baseline_final = baseline.profile_frames[-1] if baseline.profile_frames else None
            for index, candidate in enumerate(parsed_results[1:], start=1):
                candidate_final = candidate.profile_frames[-1] if candidate.profile_frames else None
                if baseline_final is None or candidate_final is None:
                    continue
                comparisons.append({
                    "direction": "candidate_minus_baseline",
                    "baseline_width_nm": inputs.feature_widths_nm[0],
                    "candidate_width_nm": inputs.feature_widths_nm[index],
                    "final_depth_difference_nm": (
                        candidate_final.depth_nm - baseline_final.depth_nm
                    ),
                    "final_aspect_ratio_difference": (
                        candidate_final.aspect_ratio - baseline_final.aspect_ratio
                    ),
                })
        statuses = {item.status for item in parsed_results}
        status = (
            "INVALID_INPUT" if "INVALID_INPUT" in statuses
            else "INSUFFICIENT_DATA" if "INSUFFICIENT_DATA" in statuses
            else "SIMULATED"
        )
        return TypeAdapter(JsonValue).validate_python({
            **common,
            "status": status,
            "process_series": [item.model_dump(mode="json") for item in points],
            "calculation_conditions": conditions,
            "simulations": simulations,
            "comparisons": comparisons,
            "warnings": [
                "실측 보정되지 않은 교육용 가정 모델이며 원인·Lot 판정 근거가 아닙니다."
            ],
        })

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
        analyze_mock_fab_run,
        simulate_mock_fab_etch,
        list_investigations,
    ]
