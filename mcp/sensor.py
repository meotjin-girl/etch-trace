# pyright: reportAny=false
"""Sensor MCP for read-only Mock Fab run retrieval and deterministic analysis."""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

from fastmcp import FastMCP
from pydantic import TypeAdapter
from sensor_models import (
    SensorAnalysis,
    SensorAnalysisInput,
    SensorDescriptor,
    SensorRun,
)
from sensor_models import (
    analyze_sensor_timeseries as analyze,
)

mcp = FastMCP("etch-sensor", version="1.0.0")


@mcp.tool
def analyze_sensor_timeseries(inputs: SensorAnalysisInput) -> SensorAnalysis:
    """Analyze provided etch sensor samples.

    Solves: first observed anomaly time, min/max, setpoint deviation, prior comparable
    run deviation, anomaly duration, co-occurring sensors, and alarm/OCAP linkage.
    Requires timestamped or offset sensor samples and comparable prior runs. It does not
    infer causality, component failure, etch rate, recipe changes, or lot disposition.
    """
    return analyze(inputs)


@mcp.tool
def analyze_current_etch_run(
    equipment: str | None = None,
    chamber: str | None = None,
    recipe: str | None = None,
    step: str | None = None,
    target_run_id: str | None = None,
) -> SensorAnalysis:
    """Retrieve and analyze a Mock Fab run plus earlier comparable normal candidates.

    Solves: connects TRACE scope to the collector's 5-second synthetic sensor history.
    The result remains synthetic evidence and never represents an approved production
    limit. Missing collector history returns INSUFFICIENT_DATA instead of invented values.
    """
    collector_url = os.getenv("FAB_COLLECTOR_URL", "").rstrip("/")
    if not collector_url:
        return SensorAnalysis(
            status="INSUFFICIENT_DATA", missing_fields=["FAB_COLLECTOR_URL"],
            warnings=["Mock Fab collector가 연결되지 않았습니다."],
        )
    try:
        with urlopen(f"{collector_url}/api/runs", timeout=10) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError) as error:
        return SensorAnalysis(
            status="INSUFFICIENT_DATA", missing_fields=["collector_run_history"],
            warnings=[f"Mock Fab run history 조회 실패 ({type(error).__name__})"],
        )
    runs = TypeAdapter(list[SensorRun]).validate_python(payload.get("runs", []))
    descriptors = TypeAdapter(list[SensorDescriptor]).validate_python(
        payload.get("sensors", []),
    )
    candidates = [
        run for run in runs
        if (target_run_id is None or run.run_id == target_run_id)
        and (equipment is None or run.equipment == equipment)
        and (chamber is None or run.chamber == chamber)
        and (recipe is None or run.recipe == recipe)
        and (step is None or run.step == step)
    ]
    if not candidates:
        return SensorAnalysis(
            status="INSUFFICIENT_DATA", missing_fields=["matching_target_run"],
            warnings=["요청 범위와 일치하는 Mock Fab Run이 없습니다."],
        )
    target = max(candidates, key=lambda run: run.started_at)
    references = [run for run in runs if run.run_id != target.run_id]
    return analyze(SensorAnalysisInput(
        target=target, references=references, sensors=descriptors,
    ))


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
