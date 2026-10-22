"""Synthetic etch sensor model derived from data/etch_root_cause_mock_v1. Not real equipment values."""

import math
import random
from collections.abc import Iterator

RECIPE_ID = "RCP-OX-ETCH-EDU-01"
SAMPLE_S = 5
RUN_S = 120
FAULT_START_S = 50

SETPOINTS = {
    "pressure_sp_mtorr": 25.0,
    "source_rf_sp_w": 900.0,
    "bias_rf_sp_w": 120.0,
    "gas_sf6_sp_sccm": 100.0,
    "gas_o2_sp_sccm": 12.0,
    "esc_temp_sp_c": 20.0,
    "backside_he_sp_torr": 8.0,
}

# name: (mean, sd, floor, subsystem, unit, ocap) from the 3 NORMAL lots (75 rows)
SENSORS = {
    "pressure_pv_mtorr": (25.013, 0.163, None, "vac", "mTorr", "OCAP-VAC-01"),
    "throttle_valve_pct": (44.003, 0.655, None, "vac", "%", "OCAP-VAC-01"),
    "source_rf_pv_w": (900.375, 4.837, None, "rf", "W", "OCAP-RF-01"),
    "source_rf_reflected_w": (5.364, 0.590, 4.5, "rf", "W", "OCAP-RF-01"),
    "bias_rf_pv_w": (120.134, 1.448, None, "rf", "W", "OCAP-RF-01"),
    "bias_rf_reflected_w": (2.491, 0.343, 2.0, "rf", "W", "OCAP-RF-01"),
    "gas_sf6_pv_sccm": (99.975, 0.429, None, "gas", "sccm", "OCAP-GAS-01"),
    "gas_o2_pv_sccm": (11.986, 0.103, None, "gas", "sccm", "OCAP-GAS-01"),
    "esc_temp_pv_c": (19.978, 0.144, None, "esc", "degC", "OCAP-ESC-01"),
    "backside_he_pv_torr": (7.997, 0.076, None, "esc", "Torr", "OCAP-ESC-01"),
    "chiller_temp_pv_c": (18.003, 0.102, None, "esc", "degC", "OCAP-ESC-01"),
    "oes_intensity_au": (5102.127, 44.067, None, "plasma", "au", "OCAP-PLASMA-01"),
}

CONTEXT = ("lot_id", "wafer_id", "recipe_id", "recipe_step", "process_state", "run_no", "sample_offset_s")
FLAGS = ("plasma_detected", "sensor_data_quality")

# SVID = chamber band + offset; secsgem reserves 1001..1005.
CHAMBER_BAND = {"CH-A": 1100, "CH-B": 2100}
SVID_OFFSET = (
    {name: i for i, name in enumerate(CONTEXT)}
    | {name: 10 + i for i, name in enumerate(SETPOINTS)}
    | {name: 20 + i for i, name in enumerate(SENSORS)}
    | {name: 40 + i for i, name in enumerate(FLAGS)}
)
ALID_OFFSET = 400
CEID_RUN_START, CEID_RUN_END = 900, 901

# name: (sensor, comparison, limit, ocap); hard interlock limits the equipment itself reports via S5F1
ALARMS = {
    "PRESSURE_HIGH": ("pressure_pv_mtorr", ">=", 30.0, "OCAP-VAC-01"),
    "THROTTLE_SATURATION": ("throttle_valve_pct", ">=", 86.0, "OCAP-VAC-01"),
    "RF_REFLECT_HIGH": ("source_rf_reflected_w", ">=", 37.0, "OCAP-RF-01"),
    "RF_SOURCE_LOW": ("source_rf_pv_w", "<=", 790.0, "OCAP-RF-01"),
    "MFC_FLOW_LOW": ("gas_sf6_pv_sccm", "<=", 87.0, "OCAP-GAS-01"),
    "MFC_FLOW_HIGH": ("gas_o2_pv_sccm", ">=", 15.0, "OCAP-GAS-01"),
    "HE_BACKSIDE_LOW": ("backside_he_pv_torr", "<=", 6.1, "OCAP-ESC-01"),
    "ESC_TEMP_HIGH": ("esc_temp_pv_c", ">=", 25.0, "OCAP-ESC-01"),
    "OES_INTENSITY_DROP": ("oes_intensity_au", "<=", 3750.0, "OCAP-PLASMA-01"),
    "PLASMA_IGNITION_DELAY": ("plasma_detected", "<=", 0, "OCAP-PLASMA-01"),
}

# scenario: sensor delta reached at RUN_S, ramped linearly from FAULT_START_S
RAMPS = {
    "PRESSURE_HIGH": {"pressure_pv_mtorr": 12, "throttle_valve_pct": 8},
    "PRESSURE_DRIFT": {"pressure_pv_mtorr": 5.4, "throttle_valve_pct": 4},
    "THROTTLE_STUCK": {"throttle_valve_pct": 52, "pressure_pv_mtorr": 6.3},
    "RF_REFLECT": {"source_rf_reflected_w": 78, "source_rf_pv_w": -45, "oes_intensity_au": -300},
    "RF_SOURCE_LOW": {"source_rf_pv_w": -155, "oes_intensity_au": -610},
    "MFC_GAS_A_LOW": {"gas_sf6_pv_sccm": -23, "oes_intensity_au": -430},
    "MFC_GAS_B_HIGH": {"gas_o2_pv_sccm": 6.2, "oes_intensity_au": 200},
    "HE_LEAK": {"backside_he_pv_torr": -3.2, "esc_temp_pv_c": 1.7},
    "ESC_TEMP_HIGH": {"esc_temp_pv_c": 8.5},
    "OES_DROP": {"oes_intensity_au": -1880},
    "MULTI_FAULT": {
        "pressure_pv_mtorr": 8.2,
        "source_rf_reflected_w": 48,
        "gas_sf6_pv_sccm": -15.6,
        "oes_intensity_au": -860,
    },
}
SCENARIOS = (*RAMPS, "PRESSURE_OSC", "SENSOR_STALE", "IGNITION_DELAY")

_A = ("HE_LEAK", "IGNITION_DELAY", "MULTI_FAULT", "PRESSURE_DRIFT", "RF_SOURCE_LOW")
_B = ("MFC_GAS_B_HIGH", "OES_DROP", "PRESSURE_HIGH", "RF_REFLECT", "SENSOR_STALE")
_C = ("ESC_TEMP_HIGH", "MFC_GAS_A_LOW", "PRESSURE_OSC", "THROTTLE_STUCK")
# fault pool per (tool, chamber) as observed in 01_equipment_lots.csv
FAULTS = {
    ("ETCH-01", "CH-A"): _A,
    ("ETCH-01", "CH-B"): _B,
    ("ETCH-02", "CH-A"): _B,
    ("ETCH-02", "CH-B"): _C,
    ("ETCH-03", "CH-A"): _C,
    ("ETCH-03", "CH-B"): _A,
}


def run_samples(scenario: str, rng: random.Random, noise: float = 1.0) -> Iterator[dict]:
    """Yield one run of 25 samples (offset 0..120 s): setpoints, sensors and flags."""
    frozen = None
    for offset in range(0, RUN_S + 1, SAMPLE_S):
        values = dict(SETPOINTS)
        for name, (mean, sd, floor, *_) in SENSORS.items():
            v = rng.gauss(mean, sd * noise)
            values[name] = max(v, floor) if floor is not None else v
        values["plasma_detected"] = 1
        values["sensor_data_quality"] = "GOOD"

        progress = max(0.0, (offset - FAULT_START_S) / (RUN_S - FAULT_START_S))
        for name, delta in RAMPS.get(scenario, {}).items():
            values[name] += delta * progress
        if scenario == "PRESSURE_OSC" and offset >= FAULT_START_S:
            wave = math.sin(2 * math.pi * (offset - FAULT_START_S) / 20)
            values["pressure_pv_mtorr"] += 3.7 * wave
            values["throttle_valve_pct"] += 5.5 * wave
        if scenario == "SENSOR_STALE" and offset >= 55:
            frozen = values["pressure_pv_mtorr"] if frozen is None else frozen
            values["pressure_pv_mtorr"] = frozen
            values["sensor_data_quality"] = "SUSPECT_STALE"
        if scenario == "IGNITION_DELAY" and 40 <= offset < 70:
            values["plasma_detected"] = 0
            values["oes_intensity_au"] = rng.uniform(40, 75)

        yield {k: round(v, 3) if isinstance(v, float) else v for k, v in values.items()} | {"sample_offset_s": offset}


def active_alarms(values: dict) -> set[str]:
    """Hard-limit alarms for one sample. OES is only judged while plasma is lit."""
    return {
        name
        for name, (sensor, op, limit, _) in ALARMS.items()
        if (values[sensor] >= limit if op == ">=" else values[sensor] <= limit)
        and not (name == "OES_INTENSITY_DROP" and values["plasma_detected"] == 0)
    }
