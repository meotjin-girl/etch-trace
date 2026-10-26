import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

from simulation_models import (
    EducationalSimulationInput,
    ProcessConditionPoint,
    SensitivityCoefficient,
    simulate_educational_etch,
)


def point(offset: float, **changes) -> ProcessConditionPoint:
    data = {
        "offset_sec": offset,
        "source_rf_w": 1000, "source_rf_reference_w": 1000,
        "bias_rf_w": 200, "bias_rf_reference_w": 200,
        "pressure_mtorr": 25, "pressure_reference_mtorr": 25,
        "sf6_sccm": 100, "sf6_reference_sccm": 100,
        "o2_sccm": 10, "o2_reference_sccm": 10,
        "esc_temp_c": 20, "esc_temp_reference_c": 20,
    }
    data.update(changes)
    return ProcessConditionPoint.model_validate(data)


def simulate(points=None, **changes):
    data = {
        "base_etch_rate_nm_min": 100,
        "feature_width_nm": 100,
        "process_points": points or [point(0), point(60), point(120)],
        "source_run_id": "MOCK-RUN-1",
    }
    data.update(changes)
    return simulate_educational_etch(EducationalSimulationInput.model_validate(data))


def test_level1_integrates_simulated_rate_over_irregular_time_steps():
    result = simulate([point(0), point(30), point(90)], arde_coefficient=0)
    assert result.status == "SIMULATED"
    assert result.profile_frames[-1].depth_nm == pytest.approx(150)
    assert result.completed_levels == [1, 2, 3]


def test_level2_applies_declared_rf_sensitivity_to_relative_rate():
    result = simulate([point(0, source_rf_w=1100), point(60, source_rf_w=1100)])
    assert result.relative_rate_series[0].relative_rate == pytest.approx(1.035)
    coefficient = next(
        item for item in result.coefficients if item.variable == "source_rf"
    )
    assert coefficient.value == 0.35
    assert coefficient.calibrated is False


def test_level2_clamps_extreme_assumption_output_for_numeric_safety():
    coefficients = [
        SensitivityCoefficient(variable=name, value=100)
        for name in ["source_rf", "bias_rf", "pressure", "sf6", "o2", "esc_temp"]
    ]
    result = simulate(
        [point(0, source_rf_w=2000), point(60, source_rf_w=2000)],
        coefficients=coefficients,
    )
    assert result.relative_rate_series[0].relative_rate == 2


def test_level3_arde_reduces_later_interval_rate_as_aspect_ratio_grows():
    result = simulate()
    frames = result.profile_frames
    assert frames[1].depth_nm == pytest.approx(100)
    assert frames[2].depth_nm == pytest.approx(190.9090909)
    assert frames[2].simulated_arde_rate_nm_min < frames[0].simulated_arde_rate_nm_min


def test_level3_profile_is_fixed_width_rectangle_not_bowing_or_taper():
    result = simulate()
    final = result.profile_frames[-1]
    assert [item.x_nm for item in final.removed_region] == [-50, 50, 50, -50]
    assert final.opening_width_nm == 100
    assert any("Bowing" in warning for warning in result.warnings)


def test_simulation_is_always_unvalidated_and_explicitly_educational():
    result = simulate(arde_coefficient_source="user_input")
    assert result.mode == "EDUCATIONAL_ASSUMPTION"
    assert result.validation_status == "NOT_VALIDATED"
    assert result.causal_conclusion is False
    assert result.arde_coefficient == 0.10
    assert result.arde_coefficient_calibrated is False
    assert result.arde_coefficient_source == "user_input"
    assert all(not coefficient.calibrated for coefficient in result.coefficients)


def test_missing_rate_width_and_series_do_not_create_a_prediction():
    result = simulate_educational_etch(EducationalSimulationInput())
    assert result.status == "INSUFFICIENT_DATA"
    assert set(result.missing_fields) == {
        "base_etch_rate_nm_min", "feature_width_nm", "at_least_two_process_points",
    }
    assert result.profile_frames == []


def test_zero_reference_or_nonpositive_width_is_rejected():
    result = simulate(
        [point(0, pressure_reference_mtorr=0), point(60)], feature_width_nm=0,
    )
    assert result.status == "INVALID_INPUT"
    assert any("non-zero" in warning for warning in result.warnings)
    assert any("positive" in warning for warning in result.warnings)


def test_non_increasing_process_offsets_are_rejected_without_reordering():
    result = simulate([point(10), point(5)])

    assert result.status == "INVALID_INPUT"
    assert result.profile_frames == []
    assert any("strictly increasing" in warning for warning in result.warnings)
