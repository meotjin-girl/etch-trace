import pytest
from pydantic import ValidationError
from v1_models import Report


def test_report_accepts_versioned_physics_result_and_legacy_default():
    legacy = Report()
    report = Report.model_validate({
        "physicsResults": [{
            "model": "etch_depth_constant_rate",
            "version": "1.0",
            "status": "calculated",
            "formula": "D = R * t",
            "inputs": [
                {"key": "etch_rate_nm_min", "value": 500, "unit": "nm/min", "source": "user_input"},
                {"key": "etch_time_sec", "value": 120, "unit": "s", "source": "user_input"},
            ],
            "result": {
                "key": "expected_etch_depth_nm",
                "value": 1000,
                "unit": "nm",
                "source": "calculated",
            },
            "assumptions": ["constant rate"],
            "missing_fields": [],
            "warnings": ["not measured"],
        }],
        "stages": [{
            "key": "physics",
            "title": "물리 관계식 검증 에이전트",
            "status": "partial",
        }],
    })
    assert legacy.physicsResults == []
    assert report.physicsResults[0].result is not None
    assert report.physicsResults[0].result.value == 1000


def test_report_rejects_unknown_physics_status():
    with pytest.raises(ValidationError):
        Report.model_validate({
            "physicsResults": [{
                "model": "selectivity",
                "status": "guessed",
                "formula": "S = R_target / R_mask",
            }],
        })
