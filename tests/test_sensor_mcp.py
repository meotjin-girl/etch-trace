import io
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

import sensor


def test_sensor_mcp_reports_missing_collector_without_fabricating_data(monkeypatch):
    monkeypatch.delenv("FAB_COLLECTOR_URL", raising=False)

    result = sensor.analyze_current_etch_run(
        equipment="ETCH-01", chamber="CH-A", lot_id="LOT-1",
        wafer_id="LOT-1-W01", recipe="RCP-1",
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.target_run_id is None
    assert result.process_series == []
    assert result.missing_fields == ["FAB_COLLECTOR_URL"]


def test_sensor_mcp_reads_collector_run_history(monkeypatch):
    payload = {
        "sensors": [{
            "name": "pressure_pv_mtorr", "unit": "mTorr",
            "normal_mean": 25, "normal_std": 1, "ocap_id": "OCAP-ETCH-PRS",
            "setpoint_key": "pressure_sp_mtorr", "alarm_names": ["PRESSURE_HIGH"],
        }],
        "runs": [{
            "run_id": "ETCH-01:CH-B:4", "equipment": "ETCH-01", "chamber": "CH-B",
            "lot_id": "LOT-4", "wafer_id": "LOT-4-W01",
            "recipe": "RCP-1", "step": "MAIN_ETCH",
            "started_at": datetime(2026, 10, 23, 12, tzinfo=UTC).isoformat(),
            "ended_at": (
                datetime(2026, 10, 23, 12, tzinfo=UTC) + timedelta(seconds=120)
            ).isoformat(),
            "normal_candidate": False,
            "samples": [{
                "offset_sec": 0, "values": {"pressure_pv_mtorr": 31},
                "setpoints": {"pressure_sp_mtorr": 25},
                "alarms": [{"alarm": "PRESSURE_HIGH", "ocap": "OCAP-ETCH-PRS"}],
                "quality": "GOOD",
            }],
        }],
    }
    monkeypatch.setenv("FAB_COLLECTOR_URL", "http://collector")
    monkeypatch.setattr(sensor, "urlopen", lambda *_args, **_kwargs: io.BytesIO(
        json.dumps(payload).encode(),
    ))
    result = sensor.analyze_current_etch_run(
        equipment="ETCH-01", chamber="CH-B", lot_id="LOT-4",
        wafer_id="LOT-4-W01", recipe="RCP-1", require_completed=True,
    )
    assert result.status == "CALCULATED"
    assert result.target_run_id == "ETCH-01:CH-B:4"
    assert result.lot_id == "LOT-4"
    assert result.wafer_id == "LOT-4-W01"
    assert result.signals[0].first_anomaly_sec == 0
    assert result.signals[0].related_alarms == ["PRESSURE_HIGH"]


def test_sensor_mcp_never_substitutes_a_different_lot_or_wafer(monkeypatch):
    payload = {
        "sensors": [],
        "runs": [{
            "run_id": "RUN-OTHER", "equipment": "ETCH-01", "chamber": "CH-A",
            "lot_id": "LOT-OTHER", "wafer_id": "LOT-OTHER-W01",
            "recipe": "RCP-1", "step": "MAIN_ETCH",
            "started_at": datetime(2026, 10, 23, 12, tzinfo=UTC).isoformat(),
            "ended_at": datetime(2026, 10, 23, 12, 2, tzinfo=UTC).isoformat(),
            "samples": [],
        }],
    }
    monkeypatch.setenv("FAB_COLLECTOR_URL", "http://collector")
    monkeypatch.setattr(sensor, "urlopen", lambda *_args, **_kwargs: io.BytesIO(
        json.dumps(payload).encode(),
    ))

    result = sensor.analyze_current_etch_run(
        equipment="ETCH-01", chamber="CH-A", lot_id="LOT-TARGET",
        wafer_id="LOT-TARGET-W01", recipe="RCP-1", require_completed=True,
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.target_run_id is None
    assert result.missing_fields == ["matching_completed_target_run"]


def test_sensor_mcp_rejects_run_when_requested_identity_is_unavailable(monkeypatch):
    payload = {
        "sensors": [],
        "runs": [{
            "run_id": "RUN-LEGACY", "equipment": "ETCH-01", "chamber": "CH-A",
            "recipe": "RCP-1", "step": "MAIN_ETCH",
            "started_at": datetime(2026, 10, 23, 12, tzinfo=UTC).isoformat(),
            "ended_at": datetime(2026, 10, 23, 12, 2, tzinfo=UTC).isoformat(),
            "samples": [],
        }],
    }
    monkeypatch.setenv("FAB_COLLECTOR_URL", "http://collector")
    monkeypatch.setattr(sensor, "urlopen", lambda *_args, **_kwargs: io.BytesIO(
        json.dumps(payload).encode(),
    ))

    result = sensor.analyze_current_etch_run(
        equipment="ETCH-01", chamber="CH-A", lot_id="LOT-TARGET",
        wafer_id="LOT-TARGET-W01", recipe="RCP-1",
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.missing_fields == ["target_run_identity"]
