# pyright: reportArgumentType=false, reportUnannotatedClassAttribute=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Pure, versioned quantitative analysis for etch investigations."""

from __future__ import annotations

import math
from datetime import datetime
from statistics import mean, pstdev
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantitativeValue(Model):
    key: str
    value: float
    unit: str
    origin: Literal["MEASURED", "CALCULATED", "SIMULATED"]
    source: str


class ControlLimit(Model):
    lower: float | None = None
    upper: float | None = None
    unit: str
    approved: bool = False
    document_id: str | None = None
    revision: str | None = None


class QuantitativeResult(Model):
    analysis: Literal[
        "reference_run_comparison", "time_resolved_etch_depth", "metrology_comparison",
    ]
    version: Literal["2.0"] = "2.0"
    problem: str
    status: Literal["CALCULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    value_origin: Literal["MEASURED", "CALCULATED", "SIMULATED"] | None = None
    validation_status: Literal["VALIDATED", "NOT_VALIDATED"] = "NOT_VALIDATED"
    formula: str
    inputs: list[QuantitativeValue] = Field(default_factory=list)
    results: list[QuantitativeValue] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    interpretation: str = ""
    recommended_checks: list[str] = Field(default_factory=list)
    within_control_limit: bool | None = None
    control_limit: ControlLimit | None = None


class RateInterval(Model):
    start_sec: float
    end_sec: float
    etch_rate_nm_min: float
    origin: Literal["MEASURED", "SIMULATED"]
    source: str


class RateSeriesInput(Model):
    intervals: list[RateInterval] = Field(default_factory=list)


class MetrologyComparisonInput(Model):
    measured_value: float | None = None
    expected_value: float | None = None
    unit: str = "nm"
    measured_key: str = "measured_etch_depth_nm"
    expected_key: str = "target_etch_depth_nm"
    measurement_source: str = "metrology"
    expected_source: str = "recipe_target"
    control_limit: ControlLimit | None = None


class ReferenceObservation(Model):
    run_id: str
    equipment: str
    chamber: str
    recipe: str
    step: str
    ended_at: datetime
    measurement_condition_id: str
    value: float
    unit: str
    normal: bool = True


class ReferenceComparisonInput(Model):
    target_run_id: str
    equipment: str
    chamber: str
    recipe: str
    step: str
    target_started_at: datetime
    measurement_condition_id: str
    target_value: float
    unit: str
    references: list[ReferenceObservation] = Field(default_factory=list)
    minimum_reference_runs: int = Field(default=3, ge=2)
    measurement_resolution: float | None = Field(default=None, gt=0)
    control_limit: ControlLimit | None = None


class EtchQuantitativeInputs(Model):
    measured_etch_depth_nm: float | None = None
    target_etch_depth_nm: float | None = None
    depth_control_limit: ControlLimit | None = None
    rate_intervals: list[RateInterval] = Field(default_factory=list)


def _finite(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def integrate_etch_rate_series(data: RateSeriesInput) -> QuantitativeResult:
    """Integrate explicit interval rates; never derive rates from process sensors."""
    common = {
        "analysis": "time_resolved_etch_depth",
        "problem": "시간에 따라 변하는 실측 또는 명시적 가정 식각률의 누적 제거 깊이 계산",
        "formula": "D = sum(R_i * delta_t_i / 60)",
        "recommended_checks": ["식각률 측정 출처", "구간 경계", "누락 구간"],
    }
    if not data.intervals:
        return QuantitativeResult(
            status="INSUFFICIENT_DATA", missing_fields=["rate_intervals"], **common,
        )
    inputs: list[QuantitativeValue] = []
    depth = 0.0
    previous_end: float | None = None
    warnings: list[str] = []
    for index, interval in enumerate(data.intervals):
        values = [interval.start_sec, interval.end_sec, interval.etch_rate_nm_min]
        if not _finite(values):
            warnings.append(f"intervals[{index}] values must be finite")
        if interval.start_sec < 0 or interval.end_sec <= interval.start_sec:
            warnings.append(f"intervals[{index}] must have a positive ordered duration")
        if interval.etch_rate_nm_min < 0:
            warnings.append(f"intervals[{index}].etch_rate_nm_min must be non-negative")
        if previous_end is not None and interval.start_sec < previous_end:
            warnings.append(f"intervals[{index}] overlaps the previous interval")
        previous_end = interval.end_sec
        inputs.append(QuantitativeValue(
            key=f"rate_interval_{index}", value=interval.etch_rate_nm_min,
            unit="nm/min", origin=interval.origin, source=interval.source,
        ))
        depth += interval.etch_rate_nm_min * (interval.end_sec - interval.start_sec) / 60
    if warnings or not math.isfinite(depth):
        if not math.isfinite(depth):
            warnings.append("calculated depth is not finite")
        return QuantitativeResult(status="INVALID_INPUT", inputs=inputs, warnings=warnings, **common)
    simulated = any(interval.origin == "SIMULATED" for interval in data.intervals)
    origin = "SIMULATED" if simulated else "CALCULATED"
    return QuantitativeResult(
        status="CALCULATED", value_origin=origin,
        validation_status="NOT_VALIDATED" if simulated else "VALIDATED",
        inputs=inputs,
        results=[QuantitativeValue(
            key="cumulative_etch_depth_nm", value=depth, unit="nm",
            origin=origin, source="interval_integration",
        )],
        warnings=(
            ["가정 기반 식각률 구간을 포함하므로 현장 데이터로 검증되지 않은 시뮬레이션입니다."]
            if simulated else []
        ),
        interpretation="명시적으로 제공된 식각률 구간만 적분했습니다.",
        **common,
    )


def compare_metrology_to_spec(data: MetrologyComparisonInput) -> QuantitativeResult:
    """Compare measured and expected values only when metrology and approved limits exist."""
    common = {
        "analysis": "metrology_comparison",
        "problem": "실측 공정 결과와 목표값 및 승인 품질 관리 규격의 편차 확인",
        "formula": "error = measured - expected; relative_error = error / expected * 100",
        "recommended_checks": ["계측 원본", "계측 위치", "승인 규격 버전"],
    }
    missing = []
    if data.measured_value is None:
        missing.append("measured_value")
    if data.expected_value is None:
        missing.append("expected_value")
    if data.control_limit is None or not data.control_limit.approved:
        missing.append("approved_control_limit")
    if missing:
        return QuantitativeResult(
            status="INSUFFICIENT_DATA", missing_fields=missing,
            control_limit=data.control_limit, **common,
        )
    assert data.measured_value is not None and data.expected_value is not None
    assert data.control_limit is not None
    values = [data.measured_value, data.expected_value]
    if not _finite(values) or data.expected_value == 0:
        return QuantitativeResult(
            status="INVALID_INPUT",
            warnings=["measured and expected values must be finite and expected must be non-zero"],
            control_limit=data.control_limit, **common,
        )
    if data.control_limit.unit != data.unit:
        return QuantitativeResult(
            status="INVALID_INPUT", warnings=["control limit unit does not match measurement unit"],
            control_limit=data.control_limit, **common,
        )
    error = data.measured_value - data.expected_value
    relative = error / data.expected_value * 100
    within = (
        (data.control_limit.lower is None or data.measured_value >= data.control_limit.lower)
        and (data.control_limit.upper is None or data.measured_value <= data.control_limit.upper)
    )
    return QuantitativeResult(
        status="CALCULATED", value_origin="CALCULATED", validation_status="VALIDATED",
        inputs=[
            QuantitativeValue(
                key=data.measured_key, value=data.measured_value, unit=data.unit,
                origin="MEASURED", source=data.measurement_source,
            ),
            QuantitativeValue(
                key=data.expected_key, value=data.expected_value, unit=data.unit,
                origin="CALCULATED", source=data.expected_source,
            ),
        ],
        results=[
            QuantitativeValue(
                key="absolute_error", value=error, unit=data.unit,
                origin="CALCULATED", source="metrology_comparison",
            ),
            QuantitativeValue(
                key="relative_error_pct", value=relative, unit="%",
                origin="CALCULATED", source="metrology_comparison",
            ),
        ],
        within_control_limit=within, control_limit=data.control_limit,
        interpretation=(
            "승인 관리 규격 범위 안입니다." if within else "승인 관리 규격 범위를 벗어났습니다."
        ),
        **common,
    )


def compare_reference_runs(data: ReferenceComparisonInput) -> QuantitativeResult:
    """Compare a target with prior, normal, strictly comparable reference runs."""
    common = {
        "analysis": "reference_run_comparison",
        "problem": "동일 조건의 과거 정상 Run 분포와 대상 Run의 정량 편차 확인",
        "formula": "delta = target - mean(reference); z = delta / std(reference)",
        "recommended_checks": ["기준 Run 선정 사유", "계측 조건", "대상 Run 이전 시점"],
    }
    if not math.isfinite(data.target_value):
        return QuantitativeResult(
            status="INVALID_INPUT", warnings=["target_value must be finite"], **common,
        )
    references = [
        item for item in data.references
        if item.normal
        and item.equipment == data.equipment
        and item.chamber == data.chamber
        and item.recipe == data.recipe
        and item.step == data.step
        and item.measurement_condition_id == data.measurement_condition_id
        and item.ended_at < data.target_started_at
        and item.unit == data.unit
        and math.isfinite(item.value)
    ]
    if len(references) < data.minimum_reference_runs:
        return QuantitativeResult(
            status="INSUFFICIENT_DATA", missing_fields=["comparable_prior_normal_runs"],
            reference_ids=[item.run_id for item in references],
            warnings=[
                (
                    f"비교 가능한 과거 정상 Run이 {len(references)}건이며 "
                    f"최소 {data.minimum_reference_runs}건이 필요합니다."
                )
            ],
            control_limit=data.control_limit, **common,
        )
    values = [item.value for item in references]
    reference_mean = mean(values)
    reference_std = pstdev(values)
    delta = data.target_value - reference_mean
    relative = delta / reference_mean * 100 if reference_mean else None
    floor = data.measurement_resolution or max(abs(reference_mean) * 1e-9, 1e-12)
    z_score = delta / reference_std if reference_std > floor else None
    results = [
        QuantitativeValue(
            key="reference_mean", value=reference_mean, unit=data.unit,
            origin="CALCULATED", source="prior_normal_runs",
        ),
        QuantitativeValue(
            key="reference_std", value=reference_std, unit=data.unit,
            origin="CALCULATED", source="prior_normal_runs",
        ),
        QuantitativeValue(
            key="absolute_delta", value=delta, unit=data.unit,
            origin="CALCULATED", source="reference_comparison",
        ),
    ]
    if relative is not None:
        results.append(QuantitativeValue(
            key="relative_delta_pct", value=relative, unit="%",
            origin="CALCULATED", source="reference_comparison",
        ))
    if z_score is not None:
        results.append(QuantitativeValue(
            key="z_score", value=z_score, unit="sigma",
            origin="CALCULATED", source="reference_comparison",
        ))
    limit = data.control_limit
    within: bool | None = None
    interpretation = "편차를 계산했지만 승인 관리한계가 없어 합격·불합격을 판정하지 않았습니다."
    if limit and limit.approved and limit.unit == data.unit:
        within = (
            (limit.lower is None or data.target_value >= limit.lower)
            and (limit.upper is None or data.target_value <= limit.upper)
        )
        interpretation = (
            "승인 관리 규격 범위 안입니다." if within else "승인 관리 규격 범위를 벗어났습니다."
        )
    warnings = []
    if z_score is None:
        warnings.append("기준 표준편차가 0 또는 측정 분해능 이하라 z-score를 보류했습니다.")
    if limit and limit.approved and limit.unit != data.unit:
        warnings.append("승인 관리한계 단위가 대상 값과 달라 규격 판정을 보류했습니다.")
    return QuantitativeResult(
        status="CALCULATED", value_origin="CALCULATED", validation_status="VALIDATED",
        inputs=[QuantitativeValue(
            key="target_value", value=data.target_value, unit=data.unit,
            origin="MEASURED", source=data.target_run_id,
        )],
        results=results, reference_ids=[item.run_id for item in references],
        warnings=warnings, interpretation=interpretation,
        within_control_limit=within, control_limit=limit, **common,
    )


def evaluate_etch_quantitative(data: EtchQuantitativeInputs) -> list[QuantitativeResult]:
    """Evaluate v2 analyses independently so missing inputs remain explicit."""
    return [
        compare_metrology_to_spec(MetrologyComparisonInput(
            measured_value=data.measured_etch_depth_nm,
            expected_value=data.target_etch_depth_nm,
            control_limit=data.depth_control_limit,
        )),
        integrate_etch_rate_series(RateSeriesInput(intervals=data.rate_intervals)),
    ]
