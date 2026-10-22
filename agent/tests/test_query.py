import pytest

from agent.models import Context
from agent.query import missing_fields, parse_question


def test_parse_frontend_context_when_question_contains_measurements():
    # Given
    text = ("ETCH-07 CH-B OX-120 endpoint 지연 94초, etch rate 저하 512, "
            "RF reflected power 상승 18W, pressure 불안정 42mtorr")
    # When
    context = parse_question(text)
    # Then
    assert context.equipment == "ETCH-07"
    assert context.chamber == "CH-B"
    assert context.recipe == "OX-120"
    assert context.metrics == {
        "endpoint_sec": 94, "etch_rate_nm_min": 512,
        "rf_reflected_w": 18, "pressure_mtorr": 42,
    }
    assert missing_fields(context) == []


def test_merge_when_clarification_adds_scope_and_overrides_one_metric():
    # Given
    existing = parse_question("endpoint 지연 94초 pressure 42mtorr")
    # When
    context = parse_question("ETCH 07 CH B OX-120 endpoint 95sec", existing)
    # Then
    assert context.symptom == existing.symptom
    assert context.metrics == {"endpoint_sec": 95, "pressure_mtorr": 42}
    assert context.recipe == "OX-120"
    assert existing.metrics["endpoint_sec"] == 94


@pytest.mark.parametrize("question,missing", [
    ("조사해 주세요", ["symptom", "scope"]),
    ("ETCH-07", ["symptom"]),
    ("endpoint delay", ["scope"]),
    ("CH-B endpoint delayed", []),
    ("OX-120 etch rate decreased", []),
])
def test_require_scope_and_symptom_when_intake_is_partial(question, missing):
    # Given / When
    context = parse_question(question)
    # Then
    assert missing_fields(context) == missing


def test_no_invented_metrics_when_only_symptom_is_given():
    # Given / When
    context = parse_question("ETCH-07 endpoint 지연")
    # Then
    assert context.metrics == {}
    assert parse_question("inspect").model_dump() == Context().model_dump()


def test_parse_physics_inputs_with_explicit_units_and_sources():
    context = parse_question(
        "ETCH-07 식각 속도 500 nm/min, 식각 시간 120초, "
        "식각 전 막 두께 1000nm, 식각 후 막 두께 400nm"
    )
    assert context.physics.etch_rate_nm_min == 500
    assert context.physics.etch_time_sec == 120
    assert context.physics.pre_thickness_nm == 1000
    assert context.physics.post_thickness_nm == 400
    assert set(context.physics.sources.values()) == {"user_input"}


def test_endpoint_time_is_not_reused_as_etch_duration():
    context = parse_question("ETCH-07 endpoint 지연 120초")
    assert context.metrics["endpoint_sec"] == 120
    assert context.physics.etch_time_sec is None


def test_parse_selectivity_rates_without_treating_target_as_generic_rate():
    context = parse_question(
        "ETCH-07 etch rate 저하, 목표막 식각 속도 500 nm/min, "
        "마스크 식각 속도 50 nm/min"
    )
    assert context.physics.target_etch_rate_nm_min == 500
    assert context.physics.mask_etch_rate_nm_min == 50
    assert context.physics.etch_rate_nm_min is None
