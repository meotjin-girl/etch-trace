# pyright: reportUnannotatedClassAttribute=false
"""Educational Level 2/3 etch simulations with explicit assumption boundaries."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProcessConditionPoint(Model):
    offset_sec: float
    source_rf_w: float
    source_rf_reference_w: float
    bias_rf_w: float
    bias_rf_reference_w: float
    pressure_mtorr: float
    pressure_reference_mtorr: float
    sf6_sccm: float
    sf6_reference_sccm: float
    o2_sccm: float
    o2_reference_sccm: float
    esc_temp_c: float
    esc_temp_reference_c: float
    source: str = "mock_fab_sensor"


class SensitivityCoefficient(Model):
    variable: Literal["source_rf", "bias_rf", "pressure", "sf6", "o2", "esc_temp"]
    value: float
    unit: Literal["per_relative_change"] = "per_relative_change"
    source: str = "TRACE educational assumption v1; not literature-derived or calibrated"
    calibrated: Literal[False] = False


def default_coefficients() -> list[SensitivityCoefficient]:
    """Return deliberately simple, uncalibrated demo sensitivities."""
    return [
        SensitivityCoefficient(variable="source_rf", value=0.35),
        SensitivityCoefficient(variable="bias_rf", value=0.25),
        SensitivityCoefficient(variable="pressure", value=-0.15),
        SensitivityCoefficient(variable="sf6", value=0.30),
        SensitivityCoefficient(variable="o2", value=-0.10),
        SensitivityCoefficient(variable="esc_temp", value=0.05),
    ]


class EducationalSimulationInput(Model):
    base_etch_rate_nm_min: float | None = None
    feature_width_nm: float | None = None
    arde_coefficient: float = 0.10
    arde_coefficient_source: str = (
        "TRACE educational assumption v1; not literature-derived or calibrated"
    )
    process_points: list[ProcessConditionPoint] = Field(default_factory=list)
    coefficients: list[SensitivityCoefficient] = Field(default_factory=default_coefficients)
    source_run_id: str | None = None


class RelativeRatePoint(Model):
    offset_sec: float
    relative_rate: float
    simulated_process_rate_nm_min: float
    source: str


class ProfileCoordinate(Model):
    x_nm: float
    y_nm: float


class ProfileFrame(Model):
    offset_sec: float
    depth_nm: float
    opening_width_nm: float
    aspect_ratio: float
    simulated_arde_rate_nm_min: float
    removed_region: list[ProfileCoordinate]


class EducationalSimulationResult(Model):
    version: Literal["3.0"] = "3.0"
    mode: Literal["EDUCATIONAL_ASSUMPTION"] = "EDUCATIONAL_ASSUMPTION"
    status: Literal["SIMULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    validation_status: Literal["NOT_VALIDATED"] = "NOT_VALIDATED"
    completed_levels: list[Literal[1, 2, 3]] = Field(default_factory=list)
    source_run_id: str | None = None
    arde_coefficient: float | None = None
    arde_coefficient_source: str = (
        "TRACE educational assumption v1; not literature-derived or calibrated"
    )
    arde_coefficient_calibrated: Literal[False] = False
    formulas: list[str] = Field(default_factory=list)
    coefficients: list[SensitivityCoefficient] = Field(default_factory=list)
    relative_rate_series: list[RelativeRatePoint] = Field(default_factory=list)
    profile_frames: list[ProfileFrame] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    causal_conclusion: Literal[False] = False


FORMULAS = [
    "delta_x = (x - x_reference) / abs(x_reference)",
    "relative_rate = clamp(1 + sum(beta_x * delta_x), 0.1, 2.0)",
    "R_ARDE = base_rate * relative_rate / (1 + k_ARDE * aspect_ratio)",
    "D[n+1] = D[n] + R_ARDE[n] * delta_t / 60",
    "aspect_ratio = depth / opening_width",
]

ASSUMPTIONS = [
    "Level 2 민감도 계수는 교육용 가정이며 논문·실측·장비별 DOE로 보정되지 않았습니다.",
    "각 센서 영향은 선형·독립·가산적이라고 단순화했습니다.",
    "상대 식각률은 수치 안정성을 위해 0.1~2.0으로 제한했습니다.",
    "Level 3 ARDE 식은 경험적 근사이며 모든 식각 공정에 성립하는 보편 법칙이 아닙니다.",
    "2D 형상은 폭이 일정한 직사각형 제거 영역이며 Bowing, Taper, 측벽각을 예측하지 않습니다.",
]


def _relative(value: float, reference: float) -> float:
    if reference == 0:
        raise ZeroDivisionError
    return (value - reference) / abs(reference)


def _finite_point(point: ProcessConditionPoint) -> bool:
    return all(math.isfinite(value) for value in (
        point.offset_sec, point.source_rf_w, point.source_rf_reference_w,
        point.bias_rf_w, point.bias_rf_reference_w, point.pressure_mtorr,
        point.pressure_reference_mtorr, point.sf6_sccm, point.sf6_reference_sccm,
        point.o2_sccm, point.o2_reference_sccm, point.esc_temp_c,
        point.esc_temp_reference_c,
    ))


def simulate_educational_etch(
    data: EducationalSimulationInput,
) -> EducationalSimulationResult:
    """Run Level 2 sensitivities then Level 3 ARDE and Level 1 integration."""
    missing: list[str] = []
    if data.base_etch_rate_nm_min is None:
        missing.append("base_etch_rate_nm_min")
    if data.feature_width_nm is None:
        missing.append("feature_width_nm")
    if len(data.process_points) < 2:
        missing.append("at_least_two_process_points")
    if missing:
        return EducationalSimulationResult(
            status="INSUFFICIENT_DATA", source_run_id=data.source_run_id,
            arde_coefficient=data.arde_coefficient,
            arde_coefficient_source=data.arde_coefficient_source,
            formulas=FORMULAS, coefficients=data.coefficients,
            missing_fields=missing, assumptions=ASSUMPTIONS,
            warnings=["교육용 시뮬레이션을 실행하지 않았습니다."],
        )
    assert data.base_etch_rate_nm_min is not None
    assert data.feature_width_nm is not None
    points = sorted(data.process_points, key=lambda item: item.offset_sec)
    warnings: list[str] = []
    if data.base_etch_rate_nm_min < 0:
        warnings.append("base_etch_rate_nm_min must be non-negative")
    if data.feature_width_nm <= 0:
        warnings.append("feature_width_nm must be positive")
    if data.arde_coefficient < 0 or not math.isfinite(data.arde_coefficient):
        warnings.append("arde_coefficient must be finite and non-negative")
    if not data.coefficients or len({item.variable for item in data.coefficients}) != 6:
        warnings.append("exactly one coefficient for each supported process variable is required")
    if any(not math.isfinite(item.value) for item in data.coefficients):
        warnings.append("sensitivity coefficients must be finite")
    if any(not _finite_point(point) or point.offset_sec < 0 for point in points):
        warnings.append("process point values and offsets must be finite and offsets non-negative")
    if any(right.offset_sec <= left.offset_sec for left, right in pairwise(points)):
        warnings.append("process point offsets must be strictly increasing")
    if any(reference == 0 for point in points for reference in [
        point.source_rf_reference_w, point.bias_rf_reference_w,
        point.pressure_reference_mtorr, point.sf6_reference_sccm,
        point.o2_reference_sccm, point.esc_temp_reference_c,
    ]):
        warnings.append("process reference values must be non-zero")
    if warnings:
        return EducationalSimulationResult(
            status="INVALID_INPUT", source_run_id=data.source_run_id,
            arde_coefficient=data.arde_coefficient,
            arde_coefficient_source=data.arde_coefficient_source,
            formulas=FORMULAS, coefficients=data.coefficients,
            assumptions=ASSUMPTIONS, warnings=warnings,
        )

    beta = {item.variable: item.value for item in data.coefficients}
    relative_rates: list[RelativeRatePoint] = []
    for point in points:
        deltas = {
            "source_rf": _relative(point.source_rf_w, point.source_rf_reference_w),
            "bias_rf": _relative(point.bias_rf_w, point.bias_rf_reference_w),
            "pressure": _relative(point.pressure_mtorr, point.pressure_reference_mtorr),
            "sf6": _relative(point.sf6_sccm, point.sf6_reference_sccm),
            "o2": _relative(point.o2_sccm, point.o2_reference_sccm),
            "esc_temp": _relative(point.esc_temp_c, point.esc_temp_reference_c),
        }
        raw = 1 + sum(beta[name] * value for name, value in deltas.items())
        factor = min(2.0, max(0.1, raw))
        relative_rates.append(RelativeRatePoint(
            offset_sec=point.offset_sec, relative_rate=factor,
            simulated_process_rate_nm_min=data.base_etch_rate_nm_min * factor,
            source=point.source,
        ))

    depth = 0.0
    first_rate = data.base_etch_rate_nm_min * relative_rates[0].relative_rate
    frames = [ProfileFrame(
        offset_sec=points[0].offset_sec, depth_nm=0, opening_width_nm=data.feature_width_nm,
        aspect_ratio=0, simulated_arde_rate_nm_min=first_rate,
        removed_region=_rectangle(data.feature_width_nm, 0),
    )]
    for index, (left, right) in enumerate(pairwise(points)):
        aspect_ratio = depth / data.feature_width_nm
        process_rate = data.base_etch_rate_nm_min * relative_rates[index].relative_rate
        arde_rate = process_rate / (1 + data.arde_coefficient * aspect_ratio)
        depth += arde_rate * (right.offset_sec - left.offset_sec) / 60
        next_aspect_ratio = depth / data.feature_width_nm
        next_process_rate = data.base_etch_rate_nm_min * relative_rates[index + 1].relative_rate
        next_arde_rate = next_process_rate / (
            1 + data.arde_coefficient * next_aspect_ratio
        )
        frames.append(ProfileFrame(
            offset_sec=right.offset_sec, depth_nm=depth,
            opening_width_nm=data.feature_width_nm, aspect_ratio=next_aspect_ratio,
            simulated_arde_rate_nm_min=next_arde_rate,
            removed_region=_rectangle(data.feature_width_nm, depth),
        ))
    return EducationalSimulationResult(
        status="SIMULATED", completed_levels=[1, 2, 3],
        source_run_id=data.source_run_id, arde_coefficient=data.arde_coefficient,
        arde_coefficient_source=data.arde_coefficient_source,
        formulas=FORMULAS,
        coefficients=data.coefficients, relative_rate_series=relative_rates,
        profile_frames=frames, assumptions=ASSUMPTIONS,
        warnings=[
            "교육용 가정 기반 결과입니다. 실측값, 검증된 예측값 또는 원인 판정 근거가 아닙니다.",
            "ARDE만으로 Bowing·Taper·측벽각을 물리적으로 예측하지 않았습니다.",
        ],
    )


def _rectangle(width_nm: float, depth_nm: float) -> list[ProfileCoordinate]:
    half = width_nm / 2
    return [
        ProfileCoordinate(x_nm=-half, y_nm=0),
        ProfileCoordinate(x_nm=half, y_nm=0),
        ProfileCoordinate(x_nm=half, y_nm=depth_nm),
        ProfileCoordinate(x_nm=-half, y_nm=depth_nm),
    ]
