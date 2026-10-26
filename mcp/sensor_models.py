# pyright: reportUnannotatedClassAttribute=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Pure sensor time-series analysis with explicit non-causal conclusions."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from itertools import pairwise
from statistics import mean, median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from quantitative_models import (
    QuantitativeResult,
    ReferenceComparisonInput,
    ReferenceObservation,
    compare_reference_runs,
)


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AlarmRef(Model):
    alarm: str
    ocap: str


class SensorSample(Model):
    offset_sec: float
    timestamp: datetime | None = None
    values: dict[str, float]
    setpoints: dict[str, float] = Field(default_factory=dict)
    alarms: list[AlarmRef] = Field(default_factory=list)
    quality: str = "GOOD"


class SensorRun(Model):
    run_id: str
    equipment: str
    chamber: str
    lot_id: str | None = None
    wafer_id: str | None = None
    recipe: str
    step: str
    started_at: datetime
    ended_at: datetime | None = None
    measurement_condition_id: str = "mock-fab-v1"
    normal_candidate: bool = False
    samples: list[SensorSample] = Field(default_factory=list)


class SensorDescriptor(Model):
    name: str
    unit: str
    normal_mean: float
    normal_std: float
    ocap_id: str
    setpoint_key: str | None = None
    alarm_names: list[str] = Field(default_factory=list)


class SensorAnalysisInput(Model):
    target: SensorRun
    references: list[SensorRun] = Field(default_factory=list)
    sensors: list[SensorDescriptor]
    minimum_reference_runs: int = Field(default=3, ge=2)


class SensorSignalAnalysis(Model):
    sensor: str
    unit: str
    minimum: float
    maximum: float
    mean: float
    first_anomaly_sec: float | None = None
    anomaly_duration_sec: float = 0
    maximum_setpoint_deviation: float | None = None
    reference_comparison: QuantitativeResult | None = None
    cooccurring_sensors: list[str] = Field(default_factory=list)
    related_alarms: list[str] = Field(default_factory=list)
    ocap_ids: list[str] = Field(default_factory=list)
    threshold_source: Literal["synthetic_baseline", "equipment_alarm", "none"] = "none"


class SensorProcessPoint(Model):
    """Observed Mock Fab process inputs retained for optional education simulations."""

    offset_sec: float
    source_rf_w: float
    source_rf_reference_w: float
    bias_rf_w: float
    bias_rf_reference_w: float
    pressure_mtorr: float
    pressure_reference_mtorr: float
    sf6_sccm: float
    sf6_reference_sccm: float
    o2_sccm: float
    o2_reference_sccm: float
    esc_temp_c: float
    esc_temp_reference_c: float
    source: Literal["mock_fab_sensor"] = "mock_fab_sensor"


class SensorAnalysis(Model):
    version: Literal["2.0"] = "2.0"
    problem: str = "센서 시계열에서 이상 시작·지속·동반 신호와 관련 OCAP 근거 확인"
    status: Literal["CALCULATED", "INSUFFICIENT_DATA", "INVALID_INPUT"]
    target_run_id: str | None = None
    equipment: str | None = None
    chamber: str | None = None
    lot_id: str | None = None
    wafer_id: str | None = None
    recipe: str | None = None
    step: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    snapshot_id: str | None = None
    snapshot_start_offset_sec: float | None = None
    snapshot_end_offset_sec: float | None = None
    signals: list[SensorSignalAnalysis] = Field(default_factory=list)
    process_series: list[SensorProcessPoint] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    causal_conclusion: Literal[False] = False


def _sample_period(samples: list[SensorSample]) -> float:
    intervals = [
        right.offset_sec - left.offset_sec
        for left, right in pairwise(samples)
        if right.offset_sec > left.offset_sec
    ]
    return median(intervals) if intervals else 0.0


def _duration(offsets: list[float], period: float) -> float:
    if not offsets or period <= 0:
        return 0.0
    total = period
    for left, right in pairwise(offsets):
        if 0 < right - left <= period * 1.5:
            total += right - left
        else:
            total += period
    return total


def analyze_sensor_timeseries(data: SensorAnalysisInput) -> SensorAnalysis:
    """Analyze observed values and timing without assigning component causality."""
    target = data.target
    if not target.samples:
        return SensorAnalysis(
            status="INSUFFICIENT_DATA", target_run_id=target.run_id,
            equipment=target.equipment, chamber=target.chamber,
            lot_id=target.lot_id, wafer_id=target.wafer_id,
            recipe=target.recipe, step=target.step,
            started_at=target.started_at, ended_at=target.ended_at,
            missing_fields=["target.samples"],
        )
    samples = sorted(target.samples, key=lambda item: item.offset_sec)
    if any(sample.offset_sec < 0 for sample in samples):
        return SensorAnalysis(
            status="INVALID_INPUT", target_run_id=target.run_id,
            equipment=target.equipment, chamber=target.chamber,
            lot_id=target.lot_id, wafer_id=target.wafer_id,
            recipe=target.recipe, step=target.step,
            started_at=target.started_at, ended_at=target.ended_at,
            warnings=["sample offsets must be non-negative"],
        )
    period = _sample_period(samples)
    descriptors = {item.name: item for item in data.sensors}
    anomaly_offsets: dict[str, list[float]] = {}
    analyses: list[SensorSignalAnalysis] = []
    for sensor, descriptor in descriptors.items():
        observed = [
            sample for sample in samples
            if sample.quality == "GOOD"
            and sensor in sample.values
            and math.isfinite(sample.values[sensor])
        ]
        if not observed:
            continue
        values = [sample.values[sensor] for sample in observed]
        alarm_set = {
            alarm.alarm
            for sample in observed
            for alarm in sample.alarms
            if alarm.alarm in descriptor.alarm_names
        }
        alarm_ocaps = {
            alarm.ocap
            for sample in observed
            for alarm in sample.alarms
            if alarm.alarm in descriptor.alarm_names
        }
        offsets = [
            sample.offset_sec for sample in observed
            if (
                descriptor.normal_std > 0
                and abs(sample.values[sensor] - descriptor.normal_mean)
                > 3 * descriptor.normal_std
            ) or any(alarm.alarm in descriptor.alarm_names for alarm in sample.alarms)
        ]
        anomaly_offsets[sensor] = offsets
        setpoint_deviations = [
            abs(sample.values[sensor] - sample.setpoints[descriptor.setpoint_key])
            for sample in observed
            if descriptor.setpoint_key and descriptor.setpoint_key in sample.setpoints
        ]
        target_mean = mean(values)
        reference_observations = []
        for run in data.references:
            reference_values = [
                sample.values[sensor]
                for sample in run.samples
                if sample.quality == "GOOD"
                and sensor in sample.values
                and math.isfinite(sample.values[sensor])
            ]
            if not reference_values or run.ended_at is None:
                continue
            reference_observations.append(ReferenceObservation(
                run_id=run.run_id, equipment=run.equipment, chamber=run.chamber,
                recipe=run.recipe, step=run.step, ended_at=run.ended_at,
                measurement_condition_id=run.measurement_condition_id,
                value=mean(reference_values), unit=descriptor.unit,
                normal=run.normal_candidate,
            ))
        comparison = compare_reference_runs(ReferenceComparisonInput(
            target_run_id=target.run_id, equipment=target.equipment,
            chamber=target.chamber, recipe=target.recipe, step=target.step,
            target_started_at=target.started_at,
            measurement_condition_id=target.measurement_condition_id,
            target_value=target_mean, unit=descriptor.unit,
            references=reference_observations,
            minimum_reference_runs=data.minimum_reference_runs,
            measurement_resolution=max(abs(descriptor.normal_std) * 1e-6, 1e-12),
        ))
        analyses.append(SensorSignalAnalysis(
            sensor=sensor, unit=descriptor.unit, minimum=min(values), maximum=max(values),
            mean=target_mean, first_anomaly_sec=min(offsets) if offsets else None,
            anomaly_duration_sec=_duration(offsets, period),
            maximum_setpoint_deviation=max(setpoint_deviations) if setpoint_deviations else None,
            reference_comparison=comparison,
            related_alarms=sorted(alarm_set),
            ocap_ids=sorted({descriptor.ocap_id, *alarm_ocaps}),
            threshold_source="equipment_alarm" if alarm_set else (
                "synthetic_baseline" if offsets else "none"
            ),
        ))
    active_by_offset = {
        offset: {
            sensor for sensor, offsets in anomaly_offsets.items() if offset in offsets
        }
        for offset in {offset for offsets in anomaly_offsets.values() for offset in offsets}
    }
    analyses = [
        item.model_copy(update={
            "cooccurring_sensors": sorted({
                peer
                for offset in anomaly_offsets.get(item.sensor, [])
                for peer in active_by_offset.get(offset, set())
                if peer != item.sensor
            })
        })
        for item in analyses
    ]
    process_series = []
    process_mapping = {
        "source_rf_w": ("source_rf_reference_w", "source_rf_pv_w", "source_rf_sp_w"),
        "bias_rf_w": ("bias_rf_reference_w", "bias_rf_pv_w", "bias_rf_sp_w"),
        "pressure_mtorr": (
            "pressure_reference_mtorr", "pressure_pv_mtorr", "pressure_sp_mtorr",
        ),
        "sf6_sccm": ("sf6_reference_sccm", "gas_sf6_pv_sccm", "gas_sf6_sp_sccm"),
        "o2_sccm": ("o2_reference_sccm", "gas_o2_pv_sccm", "gas_o2_sp_sccm"),
        "esc_temp_c": ("esc_temp_reference_c", "esc_temp_pv_c", "esc_temp_sp_c"),
    }
    for sample in samples:
        if sample.quality != "GOOD" or not all(
            value_key in sample.values and reference_key in sample.setpoints
            for _, value_key, reference_key in process_mapping.values()
        ):
            continue
        process_payload: dict[str, float | str] = {
            "offset_sec": sample.offset_sec, "source": "mock_fab_sensor",
        }
        for output_key, (reference_output_key, value_key, reference_key) in (
            process_mapping.items()
        ):
            process_payload[output_key] = sample.values[value_key]
            process_payload[reference_output_key] = sample.setpoints[reference_key]
        process_series.append(SensorProcessPoint.model_validate(process_payload))
    warnings = [
        "동반 이상은 시간적 공존만 나타내며 인과관계나 특정 부품 고장을 의미하지 않습니다."
    ]
    if any(sample.quality != "GOOD" for sample in samples):
        warnings.append("품질 상태가 GOOD이 아닌 샘플은 수치 분석에서 제외했습니다.")
    snapshot_payload = {
        "run_id": target.run_id,
        "equipment": target.equipment,
        "chamber": target.chamber,
        "lot_id": target.lot_id,
        "wafer_id": target.wafer_id,
        "recipe": target.recipe,
        "step": target.step,
        "process_series": [item.model_dump(mode="json") for item in process_series],
    }
    snapshot_id = "sha256:" + hashlib.sha256(
        json.dumps(
            snapshot_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return SensorAnalysis(
        status="CALCULATED", target_run_id=target.run_id,
        equipment=target.equipment, chamber=target.chamber,
        lot_id=target.lot_id, wafer_id=target.wafer_id,
        recipe=target.recipe, step=target.step,
        started_at=target.started_at, ended_at=target.ended_at,
        snapshot_id=snapshot_id,
        snapshot_start_offset_sec=(process_series[0].offset_sec if process_series else None),
        snapshot_end_offset_sec=(process_series[-1].offset_sec if process_series else None),
        signals=analyses, process_series=process_series, warnings=warnings,
    )
