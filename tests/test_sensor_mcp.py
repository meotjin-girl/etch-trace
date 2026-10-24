import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "mcp"))

import sensor


def test_sensor_mcp_reads_collector_run_history(monkeypatch):
    payload = {
        "sensors": [{
            "name": "pressure_pv_mtorr", "unit": "mTorr",
            "normal_mean": 25, "normal_std": 1, "ocap_id": "OCAP-ETCH-PRS",
            "setpoint_key": "pressure_sp_mtorr", "alarm_names": ["PRESSURE_HIGH"],
        }],
        "runs": [{
            "run_id": "ETCH-01:CH-B:4", "equipment": "ETCH-01", "chamber": "CH-B",
            "recipe": "RCP-1", "step": "MAIN_ETCH",
            "started_at": datetime(2026, 10, 23, 12, tzinfo=UTC).isoformat(),
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
        equipment="ETCH-01", chamber="CH-B", recipe="RCP-1",
    )
    assert result.status == "CALCULATED"
    assert result.target_run_id == "ETCH-01:CH-B:4"
    assert result.signals[0].first_anomaly_sec == 0
    assert result.signals[0].related_alarms == ["PRESSURE_HIGH"]
