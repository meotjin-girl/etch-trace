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
        result = await tools[name].ainvoke({"inputs": payload})
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
