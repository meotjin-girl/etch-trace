import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

from physics_models import (
    PhysicsInputs,
    calculate_average_etch_rate,
    calculate_etch_depth,
    calculate_selectivity,
    evaluate_etch_physics,
)


def test_etch_depth_converts_seconds_to_minutes_and_marks_expected_value():
    result = calculate_etch_depth(PhysicsInputs(
        etch_rate_nm_min=500, etch_time_sec=120,
        sources={"etch_time_sec": "equipment_log"},
    ))
    assert result.status == "calculated"
    assert result.result is not None
    assert result.result.value == 1000
    assert result.result.key == "expected_etch_depth_nm"
    assert result.inputs[1].source == "equipment_log"
    assert "실측" in result.warnings[0]


def test_average_rate_uses_thickness_loss():
    result = calculate_average_etch_rate(PhysicsInputs(
        pre_thickness_nm=1000, post_thickness_nm=400, etch_time_sec=120,
    ))
    assert result.status == "calculated"
    assert result.result is not None
    assert result.result.value == 300


def test_selectivity_is_dimensionless_ratio():
    result = calculate_selectivity(PhysicsInputs(
        target_etch_rate_nm_min=500, mask_etch_rate_nm_min=50,
    ))
    assert result.status == "calculated"
    assert result.result is not None
    assert result.result.value == 10
    assert result.result.unit == "ratio"


def test_missing_data_is_reported_without_default_values():
    results = evaluate_etch_physics(PhysicsInputs(etch_rate_nm_min=500))
    assert results[0].status == "needs_more_data"
    assert results[0].missing_fields == ["etch_time_sec"]
    assert results[0].result is None
    assert results[1].status == "needs_more_data"
    assert results[2].status == "needs_more_data"


def test_invalid_denominator_and_physical_ranges_are_rejected():
    selectivity = calculate_selectivity(PhysicsInputs(
        target_etch_rate_nm_min=500, mask_etch_rate_nm_min=0,
    ))
    rate = calculate_average_etch_rate(PhysicsInputs(
        pre_thickness_nm=400, post_thickness_nm=500, etch_time_sec=60,
    ))
    depth = calculate_etch_depth(PhysicsInputs(
        etch_rate_nm_min=math.inf, etch_time_sec=-1,
    ))
    assert selectivity.status == "invalid_input"
    assert rate.status == "invalid_input"
    assert depth.status == "invalid_input"


def test_overflowing_calculation_is_rejected():
    result = calculate_etch_depth(PhysicsInputs(
        etch_rate_nm_min=1e308, etch_time_sec=1e308,
    ))
    assert result.status == "invalid_input"
    assert result.result is None
