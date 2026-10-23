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


def test_parse_measured_target_depth_and_only_explicitly_approved_limit():
    context = parse_question(
        "ETCH-07 식각 속도 저하, 실측 식각 깊이 920 nm, 목표 식각 깊이 1000 nm, "
        "승인 관리 범위 950~1050 nm"
    )
    assert context.physics.measured_etch_depth_nm == 920
    assert context.physics.target_etch_depth_nm == 1000
    assert context.physics.depth_control_limit is not None
    assert context.physics.depth_control_limit.approved is True


def test_unapproved_range_is_not_treated_as_approved_control_limit():
    context = parse_question(
        "ETCH-07 식각 속도 저하, 실측 식각 깊이 920 nm, 목표 식각 깊이 1000 nm, "
        "관리 범위 950~1050 nm"
    )
    assert context.physics.depth_control_limit is not None
    assert context.physics.depth_control_limit.approved is False


def test_parse_mock_fab_long_recipe_id_without_truncating_it():
    context = parse_question(
        "ETCH-01 CH-B RCP-OX-ETCH-EDU-01 pressure 불안정"
    )
    assert context.recipe == "RCP-OX-ETCH-EDU-01"
    assert missing_fields(context) == []


def test_parse_explicit_educational_arde_simulation_inputs():
    context = parse_question(
        "ETCH-01 CH-A RCP-OX-ETCH-EDU-01 ARDE 형상 시뮬레이션, "
        "식각 속도 100 nm/min, 패턴 폭 80 nm, ARDE 계수 0.12"
    )
    assert context.physics.simulation_requested is True
    assert context.physics.etch_rate_nm_min == 100
    assert context.physics.feature_width_nm == 80
    assert context.physics.arde_coefficient == 0.12
    assert context.symptom == "교육용 식각 시뮬레이션 요청"
    assert missing_fields(context) == []
