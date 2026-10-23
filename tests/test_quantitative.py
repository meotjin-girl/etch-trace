import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

from quantitative_models import (
    ControlLimit,
    MetrologyComparisonInput,
    RateInterval,
    RateSeriesInput,
    ReferenceComparisonInput,
    ReferenceObservation,
    compare_metrology_to_spec,
    compare_reference_runs,
    integrate_etch_rate_series,
)


def test_integrates_measured_rate_intervals_with_irregular_durations():
    result = integrate_etch_rate_series(RateSeriesInput(intervals=[
        RateInterval(start_sec=0, end_sec=30, etch_rate_nm_min=600,
                     origin="MEASURED", source="metrology"),
        RateInterval(start_sec=30, end_sec=90, etch_rate_nm_min=300,
                     origin="MEASURED", source="metrology"),
    ]))
    assert result.status == "CALCULATED"
    assert result.results[0].value == 600
    assert result.validation_status == "VALIDATED"


def test_simulated_interval_is_explicitly_not_validated():
    result = integrate_etch_rate_series(RateSeriesInput(intervals=[
        RateInterval(start_sec=0, end_sec=60, etch_rate_nm_min=500,
                     origin="SIMULATED", source="engineer_assumption"),
    ]))
    assert result.value_origin == "SIMULATED"
    assert result.validation_status == "NOT_VALIDATED"
    assert result.warnings


def test_rate_series_is_not_invented_when_absent():
    result = integrate_etch_rate_series(RateSeriesInput())
    assert result.status == "INSUFFICIENT_DATA"
    assert result.results == []


def test_rejects_overlapping_or_negative_rate_intervals():
    result = integrate_etch_rate_series(RateSeriesInput(intervals=[
        RateInterval(start_sec=0, end_sec=60, etch_rate_nm_min=500,
                     origin="MEASURED", source="meter"),
        RateInterval(start_sec=30, end_sec=90, etch_rate_nm_min=-1,
                     origin="MEASURED", source="meter"),
    ]))
    assert result.status == "INVALID_INPUT"
    assert len(result.warnings) == 2


def test_metrology_comparison_calculates_errors_and_approved_limit():
    result = compare_metrology_to_spec(MetrologyComparisonInput(
        measured_value=920, expected_value=1000,
        control_limit=ControlLimit(
            lower=950, upper=1050, unit="nm", approved=True,
            document_id="OCAP-ETCH-RATE", revision="1.0",
        ),
    ))
    assert result.status == "CALCULATED"
    assert [value.value for value in result.results] == [-80, -8]
    assert result.within_control_limit is False
    assert result.inputs[0].origin == "MEASURED"


def test_metrology_requires_real_measurement_and_approved_limit():
    result = compare_metrology_to_spec(MetrologyComparisonInput(
        expected_value=1000,
        control_limit=ControlLimit(lower=900, upper=1100, unit="nm", approved=False),
    ))
    assert result.status == "INSUFFICIENT_DATA"
    assert set(result.missing_fields) == {"measured_value", "approved_control_limit"}


def test_metrology_rejects_mismatched_limit_unit():
    result = compare_metrology_to_spec(MetrologyComparisonInput(
        measured_value=1000, expected_value=1000, unit="nm",
        control_limit=ControlLimit(lower=0, upper=2, unit="um", approved=True),
    ))
    assert result.status == "INVALID_INPUT"


TARGET_TIME = datetime(2026, 10, 23, 12, tzinfo=UTC)


def reference(index: int, value: float, **changes) -> ReferenceObservation:
    data = {
        "run_id": f"RUN-{index}", "equipment": "ETCH-01", "chamber": "CH-B",
        "recipe": "RCP-1", "step": "MAIN_ETCH",
        "ended_at": TARGET_TIME - timedelta(hours=index),
        "measurement_condition_id": "meter-v1", "value": value,
        "unit": "mTorr", "normal": True,
    }
    data.update(changes)
    return ReferenceObservation.model_validate(data)


def comparison_input(references, **changes) -> ReferenceComparisonInput:
    data = {
        "target_run_id": "TARGET", "equipment": "ETCH-01", "chamber": "CH-B",
        "recipe": "RCP-1", "step": "MAIN_ETCH", "target_started_at": TARGET_TIME,
        "measurement_condition_id": "meter-v1", "target_value": 28,
        "unit": "mTorr", "references": references,
    }
    data.update(changes)
    return ReferenceComparisonInput.model_validate(data)


def test_reference_comparison_returns_mean_std_delta_percent_and_z():
    result = compare_reference_runs(comparison_input([
        reference(1, 24), reference(2, 25), reference(3, 26),
    ]))
    values = {item.key: item.value for item in result.results}
    assert result.status == "CALCULATED"
    assert values["reference_mean"] == 25
    assert values["absolute_delta"] == 3
    assert "relative_delta_pct" in values and "z_score" in values
    assert result.within_control_limit is None


def test_reference_comparison_excludes_future_abnormal_and_mismatched_runs():
    refs = [
        reference(1, 24), reference(2, 25), reference(3, 26),
        reference(4, 100, ended_at=TARGET_TIME + timedelta(seconds=1)),
        reference(5, 100, normal=False),
        reference(6, 100, step="DESCUM"),
        reference(7, 100, measurement_condition_id="meter-v2"),
    ]
    result = compare_reference_runs(comparison_input(refs))
    assert result.reference_ids == ["RUN-1", "RUN-2", "RUN-3"]
    assert next(item.value for item in result.results if item.key == "reference_mean") == 25


def test_reference_comparison_needs_at_least_three_comparable_runs():
    result = compare_reference_runs(comparison_input([reference(1, 25), reference(2, 25)]))
    assert result.status == "INSUFFICIENT_DATA"
    assert result.reference_ids == ["RUN-1", "RUN-2"]


def test_zero_or_tiny_standard_deviation_suppresses_z_score():
    result = compare_reference_runs(comparison_input(
        [reference(1, 25), reference(2, 25), reference(3, 25)],
        measurement_resolution=0.01,
    ))
    assert "z_score" not in {item.key for item in result.results}
    assert "표준편차" in result.warnings[0]


def test_approved_limit_takes_priority_but_no_limit_does_not_pass_or_fail():
    refs = [reference(1, 24), reference(2, 25), reference(3, 26)]
    no_limit = compare_reference_runs(comparison_input(refs))
    approved = compare_reference_runs(comparison_input(
        refs,
        control_limit=ControlLimit(
            lower=24, upper=27, unit="mTorr", approved=True,
            document_id="OCAP-ETCH-PRS",
        ),
    ))
    assert no_limit.within_control_limit is None
    assert approved.within_control_limit is False

