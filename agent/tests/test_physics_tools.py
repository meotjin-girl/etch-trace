# Copyright 2026 TRACE contributors
"""The Agent exposes the quantitative and educational Physics MCP tools."""

from dataclasses import dataclass, field

import pytest
from pydantic import JsonValue, TypeAdapter

from trace_agent.evidence import Service
from trace_agent.tools import build_tools


@dataclass
class RecordingEvidence:
    """Capture the real tool wrapper's service, MCP name, and JSON payload."""

    calls: list[tuple[Service, str, dict[str, JsonValue]]] = field(default_factory=list)

    async def call(
        self, service: Service, name: str, arguments: dict[str, JsonValue]
    ) -> JsonValue:
        self.calls.append((service, name, arguments))
        return {"called": name}


@dataclass
class SimulationEvidence:
    """Return one stable Sensor snapshot and calculate simple Physics outputs."""

    calls: list[tuple[Service, str, dict[str, JsonValue]]] = field(default_factory=list)
    sensor_points: list[dict[str, JsonValue]] | None = None

    async def call(
        self, service: Service, name: str, arguments: dict[str, JsonValue]
    ) -> JsonValue:
        self.calls.append((service, name, arguments))
        if service == "sensor":
            return TypeAdapter(JsonValue).validate_python({
                "version": "2.0",
                "problem": "Mock Fab sensor analysis",
                "status": "CALCULATED",
                "target_run_id": "ETCH-01:CH-A:7",
                "equipment": "ETCH-01",
                "chamber": "CH-A",
                "lot_id": "LOT-7",
                "wafer_id": "LOT-7-W01",
                "recipe": "RCP-1",
                "step": "MAIN_ETCH",
                "started_at": "2026-10-26T00:00:00Z",
                "ended_at": "2026-10-26T00:01:00Z",
                "snapshot_id": "sha256:snapshot-7",
                "snapshot_start_offset_sec": 0.0,
                "snapshot_end_offset_sec": 60.0,
                "process_series": (
                    self.sensor_points
                    if self.sensor_points is not None
                    else [process_point(0), process_point(60)]
                ),
                "signals": [],
                "missing_fields": [],
                "warnings": [],
                "causal_conclusion": False,
            })
        physics_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(arguments["inputs"])
        points = TypeAdapter(list[dict[str, JsonValue]]).validate_python(
            physics_inputs["process_points"]
        )
        if len(points) < 2:
            return {
                "version": "3.0", "mode": "EDUCATIONAL_ASSUMPTION",
                "status": "INSUFFICIENT_DATA", "validation_status": "NOT_VALIDATED",
                "completed_levels": [], "source_run_id": "ETCH-01:CH-A:7",
                "arde_coefficient": 0.1,
                "arde_coefficient_source": "user_input; uncalibrated educational assumption",
                "arde_coefficient_calibrated": False, "formulas": [], "coefficients": [],
                "relative_rate_series": [], "profile_frames": [],
                "missing_fields": ["at_least_two_process_points"], "assumptions": [],
                "warnings": ["교육용 시뮬레이션을 실행하지 않았습니다."],
                "causal_conclusion": False,
            }
        width = TypeAdapter(float).validate_python(physics_inputs["feature_width_nm"])
        depth = 100.0 if width == 200 else 90.0
        return {
            "version": "3.0",
            "mode": "EDUCATIONAL_ASSUMPTION",
            "status": "SIMULATED",
            "validation_status": "NOT_VALIDATED",
            "completed_levels": [1, 2, 3],
            "source_run_id": "ETCH-01:CH-A:7",
            "arde_coefficient": 0.1,
            "arde_coefficient_source": "user_input; uncalibrated educational assumption",
            "arde_coefficient_calibrated": False,
            "formulas": ["D[n+1] = D[n] + R_ARDE[n] * delta_t / 60"],
            "coefficients": [],
            "relative_rate_series": [{
                "offset_sec": 0.0, "relative_rate": 1.0,
                "simulated_process_rate_nm_min": 100.0, "source": "mock_fab_sensor",
            }],
            "profile_frames": [{
                "offset_sec": 60.0, "depth_nm": depth, "opening_width_nm": width,
                "aspect_ratio": depth / width, "simulated_arde_rate_nm_min": 90.0,
                "removed_region": [],
            }],
            "missing_fields": [],
            "assumptions": [],
            "warnings": [],
            "causal_conclusion": False,
        }


def process_point(offset_sec: float) -> dict[str, JsonValue]:
    return {
        "offset_sec": offset_sec,
        "source_rf_w": 900.0, "source_rf_reference_w": 900.0,
        "bias_rf_w": 120.0, "bias_rf_reference_w": 120.0,
        "pressure_mtorr": 25.0, "pressure_reference_mtorr": 25.0,
        "sf6_sccm": 100.0, "sf6_reference_sccm": 100.0,
        "o2_sccm": 12.0, "o2_reference_sccm": 12.0,
        "esc_temp_c": 20.0, "esc_temp_reference_c": 20.0,
        "source": "mock_fab_sensor",
    }


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_physics_mcp_tools_are_registered_and_forward_typed_inputs() -> None:
    evidence = RecordingEvidence()
    tools = {item.name: item for item in build_tools(evidence)}
    payloads: dict[str, dict[str, JsonValue]] = {
        "compare_reference_runs": {
            "target_run_id": "target-1",
            "equipment": "ETCH-01",
            "chamber": "CH-A",
            "recipe": "RCP-1",
            "step": "MAIN",
            "target_started_at": "2026-10-24T01:00:00Z",
            "measurement_condition_id": "METROLOGY-1",
            "target_value": 101.0,
            "unit": "nm",
            "references": [],
        },
        "integrate_etch_rate_series": {
            "intervals": [
                {
                    "start_sec": 0,
                    "end_sec": 60,
                    "etch_rate_nm_min": 10.0,
                    "origin": "MEASURED",
                    "source": "metrology-run-1",
                }
            ]
        },
        "compare_metrology_to_spec": {
            "measured_value": 101.0,
            "expected_value": 100.0,
            "unit": "nm",
            "control_limit": {
                "lower": 95.0,
                "upper": 105.0,
                "unit": "nm",
                "approved": True,
            },
        },
        "analyze_etch_quantitatively": {
            "measured_etch_depth_nm": 101.0,
            "target_etch_depth_nm": 100.0,
            "rate_intervals": [],
        },
        "simulate_educational_etch": {},
    }

    assert set(payloads) <= set(tools)
    for name, payload in payloads.items():
        result: object = await tools[name].ainvoke({"inputs": payload})  # pyright: ignore[reportAny]
        assert result == {"called": name}

    assert [name for _, name, _ in evidence.calls] == list(payloads)
    assert all(service == "physics" for service, _, _ in evidence.calls)
    assert all(set(arguments) == {"inputs"} for _, _, arguments in evidence.calls)
    target_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(
        evidence.calls[0][2]["inputs"]
    )
    assert target_inputs["target_run_id"] == "target-1"
    rate_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(
        evidence.calls[1][2]["inputs"]
    )
    intervals = TypeAdapter(list[dict[str, JsonValue]]).validate_python(
        rate_inputs["intervals"]
    )
    assert intervals[0]["origin"] == "MEASURED"
    simulation_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(
        evidence.calls[-1][2]["inputs"]
    )
    assert "coefficients" not in simulation_inputs


@pytest.mark.anyio
async def test_mock_fab_comparison_reuses_one_exact_sensor_snapshot() -> None:
    evidence = SimulationEvidence()
    tools = {item.name: item for item in build_tools(evidence)}

    raw: object = await tools["simulate_mock_fab_etch"].ainvoke({"inputs": {  # pyright: ignore[reportAny]
        "equipment": "ETCH-01", "chamber": "CH-A",
        "lot_id": "LOT-7", "wafer_id": "LOT-7-W01",
        "recipe": "RCP-1", "step": "MAIN_ETCH",
        "base_etch_rate_nm_min": 100.0,
        "feature_widths_nm": [200.0, 40.0],
        "arde_coefficient": 0.1,
    }})
    result = TypeAdapter(dict[str, JsonValue]).validate_python(raw)

    assert result["status"] == "SIMULATED"
    assert result["snapshot_id"] == "sha256:snapshot-7"
    assert [service for service, _, _ in evidence.calls] == ["sensor", "physics", "physics"]
    first_physics = TypeAdapter(dict[str, JsonValue]).validate_python(evidence.calls[1][2])
    second_physics = TypeAdapter(dict[str, JsonValue]).validate_python(evidence.calls[2][2])
    first_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(first_physics["inputs"])
    second_inputs = TypeAdapter(dict[str, JsonValue]).validate_python(second_physics["inputs"])
    assert first_inputs["process_points"] == second_inputs["process_points"]
    assert first_inputs["feature_width_nm"] == 200.0
    assert second_inputs["feature_width_nm"] == 40.0
    conditions = TypeAdapter(dict[str, JsonValue]).validate_python(
        result["calculation_conditions"]
    )
    assert conditions["initial_depth_nm"] == 0.0
    assert conditions["intervals_sec"] == [60.0]
    comparison = TypeAdapter(list[dict[str, JsonValue]]).validate_python(
        result["comparisons"]
    )[0]
    assert comparison["direction"] == "candidate_minus_baseline"
    assert comparison["final_depth_difference_nm"] == -10.0


@pytest.mark.anyio
async def test_mock_fab_comparison_rejects_changed_snapshot_before_physics() -> None:
    evidence = SimulationEvidence()
    tools = {item.name: item for item in build_tools(evidence)}

    raw: object = await tools["simulate_mock_fab_etch"].ainvoke({"inputs": {  # pyright: ignore[reportAny]
        "equipment": "ETCH-01", "chamber": "CH-A",
        "lot_id": "LOT-7", "wafer_id": "LOT-7-W01",
        "recipe": "RCP-1", "target_run_id": "ETCH-01:CH-A:7",
        "expected_snapshot_id": "sha256:previous",
        "base_etch_rate_nm_min": 100.0,
        "feature_widths_nm": [40.0],
    }})
    result = TypeAdapter(dict[str, JsonValue]).validate_python(raw)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["missing_fields"] == ["matching_sensor_snapshot"]
    assert [service for service, _, _ in evidence.calls] == ["sensor"]


@pytest.mark.anyio
async def test_mock_fab_comparison_with_too_few_good_samples_is_withheld() -> None:
    evidence = SimulationEvidence(sensor_points=[process_point(0)])
    tools = {item.name: item for item in build_tools(evidence)}

    raw: object = await tools["simulate_mock_fab_etch"].ainvoke({"inputs": {  # pyright: ignore[reportAny]
        "equipment": "ETCH-01", "chamber": "CH-A",
        "lot_id": "LOT-7", "wafer_id": "LOT-7-W01", "recipe": "RCP-1",
        "base_etch_rate_nm_min": 100.0, "feature_widths_nm": [200.0],
    }})
    result = TypeAdapter(dict[str, JsonValue]).validate_python(raw)

    assert result["status"] == "INSUFFICIENT_DATA"
    simulations = TypeAdapter(list[dict[str, JsonValue]]).validate_python(
        result["simulations"]
    )
    physics_result = TypeAdapter(dict[str, JsonValue]).validate_python(
        simulations[0]["result"]
    )
    assert physics_result["missing_fields"] == ["at_least_two_process_points"]
