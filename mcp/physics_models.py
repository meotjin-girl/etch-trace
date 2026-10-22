"""Deterministic zero-order etch calculations with explicit evidence limits."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PhysicsInputs(Model):
    etch_rate_nm_min: float | None = None
    etch_time_sec: float | None = None
    pre_thickness_nm: float | None = None
    post_thickness_nm: float | None = None
    target_etch_rate_nm_min: float | None = None
    mask_etch_rate_nm_min: float | None = None
    sources: dict[str, str] = Field(default_factory=dict)


class PhysicalValue(Model):
    key: str
    value: float
    unit: str
    source: str


class PhysicsResult(Model):
    model: Literal["etch_depth_constant_rate", "average_etch_rate", "selectivity"]
    version: Literal["1.0"] = "1.0"
    status: Literal["calculated", "needs_more_data", "invalid_input"]
    formula: str
    inputs: list[PhysicalValue] = Field(default_factory=list)
    result: PhysicalValue | None = None
    assumptions: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


UNITS = {
    "etch_rate_nm_min": "nm/min",
    "etch_time_sec": "s",
    "pre_thickness_nm": "nm",
    "post_thickness_nm": "nm",
    "target_etch_rate_nm_min": "nm/min",
    "mask_etch_rate_nm_min": "nm/min",
}


def _values(data: PhysicsInputs, keys: tuple[str, ...]) -> list[PhysicalValue]:
    values = []
    for key in keys:
        value = getattr(data, key)
        if value is not None:
            values.append(PhysicalValue(
                key=key,
                value=value,
                unit=UNITS[key],
                source=data.sources.get(key, "user_input"),
            ))
    return values


def _missing(data: PhysicsInputs, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if getattr(data, key) is None]


def _invalid(data: PhysicsInputs, keys: tuple[str, ...]) -> list[str]:
    return [
        f"{key} must be finite"
        for key in keys
        if (value := getattr(data, key)) is not None and not math.isfinite(value)
    ]


def calculate_etch_depth(data: PhysicsInputs) -> PhysicsResult:
    keys = ("etch_rate_nm_min", "etch_time_sec")
    inputs = _values(data, keys)
    missing = _missing(data, keys)
    common = {
        "model": "etch_depth_constant_rate",
        "formula": "D = R * t",
        "inputs": inputs,
        "assumptions": ["식각 시간 동안 평균 식각 속도가 일정합니다."],
    }
    if missing:
        return PhysicsResult(status="needs_more_data", missing_fields=missing, **common)
    warnings = _invalid(data, keys)
    assert data.etch_rate_nm_min is not None and data.etch_time_sec is not None
    if data.etch_rate_nm_min < 0:
        warnings.append("etch_rate_nm_min must be non-negative")
    if data.etch_time_sec <= 0:
        warnings.append("etch_time_sec must be greater than zero")
    if warnings:
        return PhysicsResult(status="invalid_input", warnings=warnings, **common)
    depth = data.etch_rate_nm_min * data.etch_time_sec / 60
    if not math.isfinite(depth):
        return PhysicsResult(
            status="invalid_input", warnings=["calculated depth is not finite"], **common,
        )
    return PhysicsResult(
        status="calculated",
        result=PhysicalValue(
            key="expected_etch_depth_nm", value=depth, unit="nm", source="calculated",
        ),
        warnings=["계산 예상값이며 실측 식각 깊이가 아닙니다."],
        **common,
    )


def calculate_average_etch_rate(data: PhysicsInputs) -> PhysicsResult:
    keys = ("pre_thickness_nm", "post_thickness_nm", "etch_time_sec")
    inputs = _values(data, keys)
    missing = _missing(data, keys)
    common = {
        "model": "average_etch_rate",
        "formula": "R = (D0 - D1) / t",
        "inputs": inputs,
        "assumptions": ["전후 막 두께 차이가 해당 식각 단계에서 제거된 두께를 나타냅니다."],
    }
    if missing:
        return PhysicsResult(status="needs_more_data", missing_fields=missing, **common)
    warnings = _invalid(data, keys)
    assert data.pre_thickness_nm is not None
    assert data.post_thickness_nm is not None
    assert data.etch_time_sec is not None
    if data.pre_thickness_nm < 0 or data.post_thickness_nm < 0:
        warnings.append("film thickness must be non-negative")
    if data.etch_time_sec <= 0:
        warnings.append("etch_time_sec must be greater than zero")
    if data.post_thickness_nm > data.pre_thickness_nm:
        warnings.append("post_thickness_nm exceeds pre_thickness_nm")
    if warnings:
        return PhysicsResult(status="invalid_input", warnings=warnings, **common)
    rate = (data.pre_thickness_nm - data.post_thickness_nm) / data.etch_time_sec * 60
    if not math.isfinite(rate):
        return PhysicsResult(
            status="invalid_input", warnings=["calculated etch rate is not finite"], **common,
        )
    return PhysicsResult(
        status="calculated",
        result=PhysicalValue(
            key="average_etch_rate_nm_min", value=rate, unit="nm/min", source="calculated",
        ),
        **common,
    )


def calculate_selectivity(data: PhysicsInputs) -> PhysicsResult:
    keys = ("target_etch_rate_nm_min", "mask_etch_rate_nm_min")
    inputs = _values(data, keys)
    missing = _missing(data, keys)
    common = {
        "model": "selectivity",
        "formula": "S = R_target / R_mask",
        "inputs": inputs,
        "assumptions": ["두 식각 속도는 비교 가능한 동일 공정 조건에서 측정되었습니다."],
    }
    if missing:
        return PhysicsResult(status="needs_more_data", missing_fields=missing, **common)
    warnings = _invalid(data, keys)
    assert data.target_etch_rate_nm_min is not None
    assert data.mask_etch_rate_nm_min is not None
    if data.target_etch_rate_nm_min < 0:
        warnings.append("target_etch_rate_nm_min must be non-negative")
    if data.mask_etch_rate_nm_min <= 0:
        warnings.append("mask_etch_rate_nm_min must be greater than zero")
    if warnings:
        return PhysicsResult(status="invalid_input", warnings=warnings, **common)
    selectivity = data.target_etch_rate_nm_min / data.mask_etch_rate_nm_min
    if not math.isfinite(selectivity):
        return PhysicsResult(
            status="invalid_input", warnings=["calculated selectivity is not finite"], **common,
        )
    return PhysicsResult(
        status="calculated",
        result=PhysicalValue(
            key="selectivity_ratio",
            value=selectivity,
            unit="ratio",
            source="calculated",
        ),
        **common,
    )


def evaluate_etch_physics(data: PhysicsInputs) -> list[PhysicsResult]:
    """Evaluate all supported models; missing data is an explicit result."""
    return [
        calculate_etch_depth(data),
        calculate_average_etch_rate(data),
        calculate_selectivity(data),
    ]
