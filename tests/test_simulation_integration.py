import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

from sensor_models import SensorAnalysisInput, SensorRun, SensorSample, analyze_sensor_timeseries
from simulation_models import (
    EducationalSimulationInput,
    ProcessConditionPoint,
    simulate_educational_etch,
)


def process_sample(offset: float, source_rf: float) -> SensorSample:
    return SensorSample(
        offset_sec=offset,
        values={
            "source_rf_pv_w": source_rf, "bias_rf_pv_w": 200,
            "pressure_pv_mtorr": 25, "gas_sf6_pv_sccm": 100,
            "gas_o2_pv_sccm": 10, "esc_temp_pv_c": 20,
        },
        setpoints={
            "source_rf_sp_w": 1000, "bias_rf_sp_w": 200,
            "pressure_sp_mtorr": 25, "gas_sf6_sp_sccm": 100,
            "gas_o2_sp_sccm": 10, "esc_temp_sp_c": 20,
        },
    )


def test_mock_sensor_contract_flows_through_level2_arde_and_level1_integration():
    started = datetime(2026, 10, 23, tzinfo=UTC)
    run = SensorRun(
        run_id="ETCH-01:CH-A:1", equipment="ETCH-01", chamber="CH-A",
        recipe="RCP-OX-ETCH-EDU-01", step="MAIN_ETCH", started_at=started,
        ended_at=started + timedelta(seconds=60),
        samples=[process_sample(0, 1000), process_sample(30, 900), process_sample(60, 900)],
    )
    sensor = analyze_sensor_timeseries(SensorAnalysisInput(
        target=run, sensors=[],
    ))
    result = simulate_educational_etch(EducationalSimulationInput(
        base_etch_rate_nm_min=100, feature_width_nm=80,
        process_points=[
            ProcessConditionPoint.model_validate(item.model_dump())
            for item in sensor.process_series
        ],
        source_run_id=sensor.target_run_id,
    ))

    assert sensor.status == "CALCULATED"
    assert result.status == "SIMULATED"
    assert result.source_run_id == "ETCH-01:CH-A:1"
    assert result.relative_rate_series[1].relative_rate < 1
    assert result.profile_frames[-1].depth_nm > 0
    assert result.validation_status == "NOT_VALIDATED"
