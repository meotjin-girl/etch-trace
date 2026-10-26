import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

from sensor_models import (
    AlarmRef,
    SensorAnalysisInput,
    SensorDescriptor,
    SensorRun,
    SensorSample,
    analyze_sensor_timeseries,
)

START = datetime(2026, 10, 23, 10, tzinfo=UTC)
SENSORS = [
    SensorDescriptor(
        name="pressure_pv_mtorr", unit="mTorr", normal_mean=25, normal_std=1,
        ocap_id="OCAP-ETCH-PRS", setpoint_key="pressure_sp_mtorr",
        alarm_names=["PRESSURE_HIGH"],
    ),
    SensorDescriptor(
        name="source_rf_reflected_w", unit="W", normal_mean=5, normal_std=1,
        ocap_id="OCAP-ETCH-RF", alarm_names=["RF_REFLECT_HIGH"],
    ),
]


def sample(offset, pressure=25, reflected=5, quality="GOOD", alarms=None):
    return SensorSample(
        offset_sec=offset, timestamp=START + timedelta(seconds=offset),
        values={"pressure_pv_mtorr": pressure, "source_rf_reflected_w": reflected},
        setpoints={"pressure_sp_mtorr": 25}, quality=quality,
        alarms=alarms or [],
    )


def run(run_id, started_at, samples, normal=False):
    return SensorRun(
        run_id=run_id, equipment="ETCH-01", chamber="CH-B", recipe="RCP-1",
        step="MAIN_ETCH", started_at=started_at,
        ended_at=started_at + timedelta(seconds=120),
        normal_candidate=normal, samples=samples,
    )


def test_sensor_analysis_finds_onset_duration_setpoint_cooccurrence_and_ocap():
    target = run("TARGET", START, [
        sample(0), sample(5),
        sample(10, pressure=30, reflected=10, alarms=[
            AlarmRef(alarm="PRESSURE_HIGH", ocap="OCAP-ETCH-PRS"),
            AlarmRef(alarm="RF_REFLECT_HIGH", ocap="OCAP-ETCH-RF"),
        ]),
        sample(15, pressure=31, reflected=11),
    ])
    references = [
        run(f"REF-{index}", START - timedelta(hours=index),
            [sample(0, pressure=24 + index, reflected=4 + index)], normal=True)
        for index in range(1, 4)
    ]
    result = analyze_sensor_timeseries(SensorAnalysisInput(
        target=target, references=references, sensors=SENSORS,
    ))
    pressure = next(item for item in result.signals if item.sensor == "pressure_pv_mtorr")
    assert result.status == "CALCULATED" and result.causal_conclusion is False
    assert pressure.first_anomaly_sec == 10
    assert pressure.anomaly_duration_sec == 10
    assert pressure.maximum_setpoint_deviation == 6
    assert pressure.cooccurring_sensors == ["source_rf_reflected_w"]
    assert pressure.related_alarms == ["PRESSURE_HIGH"]
    assert pressure.ocap_ids == ["OCAP-ETCH-PRS"]
    assert pressure.reference_comparison is not None
    assert pressure.reference_comparison.status == "CALCULATED"


def test_sensor_analysis_excludes_bad_quality_samples():
    target = run("TARGET", START, [
        sample(0), sample(5, pressure=100, quality="SUSPECT_STALE"), sample(10),
    ])
    result = analyze_sensor_timeseries(SensorAnalysisInput(target=target, sensors=SENSORS))
    pressure = next(item for item in result.signals if item.sensor == "pressure_pv_mtorr")
    assert pressure.maximum == 25
    assert pressure.first_anomaly_sec is None
    assert any("GOOD" in warning for warning in result.warnings)


def test_sensor_analysis_needs_samples_and_does_not_invent_values():
    target = run("TARGET", START, [])
    result = analyze_sensor_timeseries(SensorAnalysisInput(target=target, sensors=SENSORS))
    assert result.status == "INSUFFICIENT_DATA"
    assert result.signals == []


def test_sensor_analysis_exposes_good_process_points_for_education_only():
    values = {
        "source_rf_pv_w": 1000, "bias_rf_pv_w": 200,
        "pressure_pv_mtorr": 25, "gas_sf6_pv_sccm": 100,
        "gas_o2_pv_sccm": 10, "esc_temp_pv_c": 20,
    }
    setpoints = {
        "source_rf_sp_w": 990, "bias_rf_sp_w": 195,
        "pressure_sp_mtorr": 24, "gas_sf6_sp_sccm": 98,
        "gas_o2_sp_sccm": 9, "esc_temp_sp_c": 20,
    }
    target = run("TARGET", START, [
        SensorSample(offset_sec=0, values=values, setpoints=setpoints),
        SensorSample(offset_sec=5, values=values, setpoints=setpoints),
    ])
    result = analyze_sensor_timeseries(SensorAnalysisInput(target=target, sensors=[]))
    assert len(result.process_series) == 2
    assert result.process_series[0].source_rf_w == 1000
    assert result.process_series[0].source_rf_reference_w == 990
    assert result.process_series[0].source == "mock_fab_sensor"
    assert result.snapshot_id is not None
    assert result.snapshot_id.startswith("sha256:")
    assert result.snapshot_start_offset_sec == 0
    assert result.snapshot_end_offset_sec == 5
