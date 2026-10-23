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


def test_report_accepts_v2_quantitative_and_sensor_analysis_without_breaking_v1():
    report = Report.model_validate({
        "quantitativeResults": [{
            "analysis": "metrology_comparison", "version": "2.0",
            "problem": "실측 깊이와 승인 규격 비교", "status": "CALCULATED",
            "value_origin": "CALCULATED", "validation_status": "VALIDATED",
            "formula": "error = measured - expected",
            "results": [{
                "key": "absolute_error", "value": -80, "unit": "nm",
                "origin": "CALCULATED", "source": "metrology_comparison",
            }],
            "within_control_limit": False,
            "control_limit": {
                "lower": 950, "upper": 1050, "unit": "nm", "approved": True,
                "document_id": "OCAP-ETCH-RATE", "revision": "1.0",
            },
        }],
        "sensorAnalysis": {
            "problem": "센서 시계열 정량 분석", "status": "CALCULATED",
            "target_run_id": "RUN-1", "causal_conclusion": False,
            "signals": [{
                "sensor": "pressure_pv_mtorr", "unit": "mTorr",
                "minimum": 25, "maximum": 31, "mean": 28,
                "first_anomaly_sec": 50, "anomaly_duration_sec": 20,
                "related_alarms": ["PRESSURE_HIGH"],
                "ocap_ids": ["OCAP-ETCH-PRS"],
                "threshold_source": "equipment_alarm",
            }],
        },
    })
    assert report.physicsResults == []
    assert report.quantitativeResults[0].within_control_limit is False
    assert report.sensorAnalysis is not None
    assert report.sensorAnalysis.causal_conclusion is False


def test_report_accepts_separate_unvalidated_educational_simulation():
    report = Report.model_validate({
        "educationalSimulation": {
            "status": "SIMULATED", "completed_levels": [1, 2, 3],
            "source_run_id": "MOCK-RUN-1",
            "coefficients": [{
                "variable": "source_rf", "value": 0.35,
                "source": "TRACE educational assumption v1", "calibrated": False,
            }],
            "profile_frames": [{
                "offset_sec": 60, "depth_nm": 95, "opening_width_nm": 80,
                "aspect_ratio": 1.1875, "simulated_arde_rate_nm_min": 89,
                "removed_region": [
                    {"x_nm": -40, "y_nm": 0}, {"x_nm": 40, "y_nm": 0},
                    {"x_nm": 40, "y_nm": 95}, {"x_nm": -40, "y_nm": 95},
                ],
            }],
            "warnings": ["실측값 또는 검증된 예측값이 아닙니다."],
        },
    })
    assert report.educationalSimulation is not None
    assert report.educationalSimulation.validation_status == "NOT_VALIDATED"
    assert report.educationalSimulation.coefficients[0].calibrated is False
