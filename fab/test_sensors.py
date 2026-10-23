import json
import random
import socket
import urllib.request
import datetime

import secsgem.common
import secsgem.hsms

import collector
import equipment
import sensors

EXPECTED = {
    "PRESSURE_HIGH": "PRESSURE_HIGH",
    "PRESSURE_DRIFT": "PRESSURE_HIGH",
    "THROTTLE_STUCK": "THROTTLE_SATURATION",
    "RF_REFLECT": "RF_REFLECT_HIGH",
    "RF_SOURCE_LOW": "RF_SOURCE_LOW",
    "MFC_GAS_A_LOW": "MFC_FLOW_LOW",
    "MFC_GAS_B_HIGH": "MFC_FLOW_HIGH",
    "HE_LEAK": "HE_BACKSIDE_LOW",
    "ESC_TEMP_HIGH": "ESC_TEMP_HIGH",
    "OES_DROP": "OES_INTENSITY_DROP",
    "IGNITION_DELAY": "PLASMA_IGNITION_DELAY",
    "MULTI_FAULT": "PRESSURE_HIGH",
    "PRESSURE_OSC": None,  # FDC-only
    "SENSOR_STALE": None,  # FDC-only
}


def test_every_fault_is_assigned_and_expected():
    assigned = {s for pool in sensors.FAULTS.values() for s in pool}
    assert assigned == set(sensors.SCENARIOS) == set(EXPECTED)


def test_normal_runs_stay_in_range_without_alarms():
    rng = random.Random(1)
    outside = total = 0
    for _ in range(200):
        for sample in sensors.run_samples("NORMAL", rng):
            assert sensors.active_alarms(sample) == set()
            assert sample["plasma_detected"] == 1 and sample["sensor_data_quality"] == "GOOD"
            for name, (mean, sd, *_) in sensors.SENSORS.items():
                total += 1
                outside += abs(sample[name] - mean) > 3 * sd
    assert len(list(sensors.run_samples("NORMAL", rng))) == 25
    assert outside / total < 0.01


def test_faults_alarm_only_after_onset():
    for seed in range(20):
        for scenario, alarm in EXPECTED.items():
            seen = set()
            for sample in sensors.run_samples(scenario, random.Random(seed)):
                active = sensors.active_alarms(sample)
                if sample["sample_offset_s"] < 40:
                    assert active == set(), (scenario, sample["sample_offset_s"])
                seen |= active
            assert (alarm in seen) if alarm else not seen, (scenario, seed, seen)
            if scenario != "MULTI_FAULT" and scenario != "THROTTLE_STUCK":
                assert seen <= {alarm}, (scenario, seed, seen)


def test_oscillation_and_stale_shapes():
    osc = [s["pressure_pv_mtorr"] for s in sensors.run_samples("PRESSURE_OSC", random.Random(0))]
    assert max(osc[10:]) - min(osc[10:]) > 6 and max(osc) < 30
    stale = list(sensors.run_samples("SENSOR_STALE", random.Random(0)))
    assert len({s["pressure_pv_mtorr"] for s in stale[11:]}) == 1
    assert stale[11]["sensor_data_quality"] == "SUSPECT_STALE"


def test_collector_keeps_bounded_run_history_with_step_and_samples():
    link = collector.Link("ETCH-01", "127.0.0.1", free_port())
    base = {
        "run_no": 42, "recipe_id": sensors.RECIPE_ID, "recipe_step": "MAIN_ETCH",
        "sensor_data_quality": "GOOD",
    }
    for values in sensors.run_samples("NORMAL", random.Random(42)):
        offset = values["sample_offset_s"]
        link.updated_at = (
            datetime.datetime(2026, 10, 23, tzinfo=datetime.UTC)
            + datetime.timedelta(seconds=offset)
        ).isoformat()
        link._record_run("CH-B", base | values)
    history = link.run_history()
    assert len(history) == 1
    assert history[0]["run_id"] == "ETCH-01:CH-B:42"
    assert history[0]["step"] == "MAIN_ETCH"
    assert len(history[0]["samples"]) == 25
    assert history[0]["ended_at"] is not None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_hsms_roundtrip_and_http():
    port = free_port()
    tool = equipment.Tool(
        secsgem.hsms.HsmsSettings(
            address="127.0.0.1",
            port=port,
            connect_mode=secsgem.hsms.HsmsConnectMode.PASSIVE,
            device_type=secsgem.common.DeviceType.EQUIPMENT,
        ),
        "ETCH-01",
    )
    link = collector.Link("ETCH-01", "127.0.0.1", port)
    tool.enable()
    link.host.enable()
    server = None
    try:
        assert link.host.waitfor_communicating(10)
        band = sensors.CHAMBER_BAND["CH-B"]
        sample = next(sensors.run_samples("NORMAL", random.Random(0))) | {"pressure_pv_mtorr": 31.0, "lot_id": "L1"}
        for name, value in sample.items():
            tool.values[band + sensors.SVID_OFFSET[name]] = value
        tool.sync_alarms(band, sensors.active_alarms(sample))

        link.poll()
        assert link.up
        assert link.chambers["CH-B"]["pressure_pv_mtorr"] == 31.0
        assert link.chambers["CH-B"]["lot_id"] == "L1"
        assert link.active_alarms("CH-B") == [{"alarm": "PRESSURE_HIGH", "ocap": "OCAP-ETCH-PRS"}]
        assert link.active_alarms("CH-A") == []
        assert set(tool._get_events_enabled()) == link.ceids  # first poll saw no reports and subscribed

        server = collector.serve([link], 0)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        current = json.load(urllib.request.urlopen(f"{base}/api/current"))
        assert current["synthetic"] is True
        assert {(m["tool"], m["chamber"]) for m in current["modules"]} == {("ETCH-01", "CH-A"), ("ETCH-01", "CH-B")}
        history = json.load(urllib.request.urlopen(f"{base}/api/runs"))
        assert history["synthetic"] is True
        assert {item["name"] for item in history["sensors"]} == set(sensors.SENSORS)
        metrics = urllib.request.urlopen(f"{base}/metrics").read().decode()
        assert 'etch_sensor_value{chamber="CH-B",sensor="pressure_pv_mtorr",tool="ETCH-01"} 31.0' in metrics
        assert 'etch_alarm_active{alarm="PRESSURE_HIGH",chamber="CH-B",ocap="OCAP-ETCH-PRS",tool="ETCH-01"} 1.0' in metrics
        assert "etch_run_info{" in metrics and 'lot_id="L1"' in metrics
        assert b"<title>" in urllib.request.urlopen(f"{base}/").read()
    finally:
        if server:
            server.shutdown()
        # equipment first: once the host drops, secsgem re-listens and disable() can then spin forever (0.3.0)
        tool.disable()
        link.host.disable()
