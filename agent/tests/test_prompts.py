# Copyright 2026 TRACE contributors
"""Regression checks for Physics evidence boundaries in the Agent prompts."""

from trace_agent.prompts import PROPOSAL_PROMPT, SYSTEM_PROMPT


def test_system_prompt_preserves_physics_status_and_structured_evidence() -> None:
    assert "status, missing_fields, warnings, formulas, coefficients" in SYSTEM_PROMPT
    assert "INSUFFICIENT_DATA" in SYSTEM_PROMPT
    assert "INVALID_INPUT" in SYSTEM_PROMPT
    assert "status와 누락 필드를 임의로 바꾸거나" in SYSTEM_PROMPT


def test_system_prompt_separates_completed_and_withheld_simulation() -> None:
    assert "SIMULATED일 때만 시뮬레이션을 실행" in SYSTEM_PROMPT
    assert "입력 검증 후 계산을 보류" in SYSTEM_PROMPT
    assert "빈 시계열에 대한 상대 식각률" in SYSTEM_PROMPT


def test_prompts_keep_educational_simulation_out_of_causal_evidence() -> None:
    assert "가정 기반\n교육용 결과는 SIMULATED" in SYSTEM_PROMPT
    assert "실제 원인·조치 후보의 근거" in PROPOSAL_PROMPT
