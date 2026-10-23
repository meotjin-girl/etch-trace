"""Alert intake: Prometheus bundling, fixed-format content and the role=system agent request."""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import anyio
import pytest
from conftest import Wire, detail
from fastapi.testclient import TestClient
from v1_alerts import AlertPoller, Prometheus, render, submit, summary

T0 = datetime(2026, 10, 22, 6, 14, 16, tzinfo=UTC).timestamp()  # run start, 15:14:16 KST


@dataclass
class FakePrometheus:
    lot: str = "SIMLOT-20261022-2A151416"
    alerts: list[dict] = field(default_factory=list)
    url: str = ""


def alert(name: str, active: float, value: float, **labels: str) -> dict:
    stamp = datetime.fromtimestamp(active, UTC).strftime("%Y-%m-%dT%H:%M:%S.123456789Z")
    return {
        "labels": {"alertname": name, "tool": "ETCH-02", "chamber": "CH-A", **labels},
        "state": "firing",
        "activeAt": stamp,
        "value": f"{value:e}",
    }


@pytest.fixture
def prom() -> Iterator[FakePrometheus]:
    state = FakePrometheus()

    def vector(metric: dict, value: float) -> dict:
        return {"metric": metric, "value": [T0, str(value)]}

    def answer(path: str, query: dict[str, list[str]]) -> dict:
        if path == "/api/v1/alerts":
            return {"alerts": state.alerts}
        q = query["query"][0]
        if path == "/api/v1/query_range":
            start, end = float(query["start"][0]), float(query["end"][0])
            steps = range(int(start), int(end) + 1, 5)
            series = {"source_rf_reflected_w": 5.0, "gas_sf6_pv_sccm": 100.0}
            return {"result": [
                {"metric": {"sensor": name, "tool": "ETCH-02", "chamber": "CH-A"},
                 "values": [[t, str(base + (t - start) / 5)] for t in steps if t != start + 10]}
                for name, base in series.items()
            ]}
        if q.startswith("etch_run_info"):
            run = {"tool": "ETCH-02", "chamber": "CH-A", "lot_id": state.lot, "wafer_id": f"{state.lot}-W01",
                   "recipe_id": "RCP-OX-ETCH-EDU-01", "run_no": "1101"}
            return {"result": [vector(run, 1)]}
        if q.startswith("etch_sample_offset_seconds"):
            return {"result": [vector({}, float(query["time"][0]) - T0)]}
        if q.startswith("etch_sensor_normal_"):
            sd = q.endswith("sd")
            return {"result": [
                vector({"sensor": "source_rf_reflected_w", "unit": "W", "subsystem": "rf"}, 0.59 if sd else 5.364),
                vector({"sensor": "gas_sf6_pv_sccm", "unit": "sccm", "subsystem": "gas"}, 0.429 if sd else 99.975),
            ]}
        if q.startswith("etch_sensor_value"):
            return {"result": [vector({"sensor": "source_rf_reflected_w"}, 39.42)]}
        raise AssertionError(f"unexpected query {path} {q}")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            url = urlsplit(self.path)
            body = json.dumps({"status": "success", "data": answer(url.path, parse_qs(url.query))}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: str) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def rf_alerts() -> list[dict]:
    return [
        alert("EQUIPMENT_ALARM", T0 + 80, 1, alarm="RF_REFLECT_HIGH", sensor="source_rf_reflected_w",
              limit="37", ocap="OCAP-ETCH-RF", source="equipment"),
        alert("FDC_WATCH", T0 + 55, 4.12, sensor="source_rf_reflected_w", ocap="OCAP-ETCH-RF", source="fdc"),
    ]


def test_bundle_closes_on_timeout_with_ordered_alerts(prom: FakePrometheus) -> None:
    now = [T0 + 60]
    poller = AlertPoller(Prometheus(prom.url), known=lambda key: False, clock=lambda: now[0])
    prom.alerts = rf_alerts()
    # Given firing alerts of one run, the bundle stays open until it times out.
    assert poller.poll() == []
    now[0] += 90
    [bundle] = poller.poll()
    assert bundle.key == "ETCH-02/CH-A/SIMLOT-20261022-2A151416"
    assert [a.rule for a in bundle.alerts] == ["FDC_WATCH", "RF_REFLECT_HIGH"]
    equipment = bundle.alerts[1]
    assert (equipment.source, equipment.value, equipment.limit, equipment.unit) == ("equipment", 39.42, 37, "W")
    assert bundle.window.start.isoformat() == "2026-10-22T06:14:16+00:00"  # first activeAt minus sample offset
    # The same key never closes twice while its alerts keep firing.
    now[0] += 90
    assert poller.poll() == []


def test_bundle_closes_when_lot_changes_and_skips_known_keys(prom: FakePrometheus) -> None:
    poller = AlertPoller(Prometheus(prom.url), known=lambda key: key.endswith("KNOWN"), clock=lambda: T0 + 60)
    prom.alerts = rf_alerts()
    assert poller.poll() == []
    prom.lot = "SIMLOT-20261022-2A151621"
    assert len(poller.poll()) == 1
    # A key already recorded in the database (e.g. before a restart) is not reopened.
    prom.lot = "KNOWN"
    fresh = AlertPoller(Prometheus(prom.url), known=lambda key: key.endswith("KNOWN"), clock=lambda: T0 + 600)
    assert fresh.poll() == [] and fresh.open == {}


def test_render_follows_the_documented_line_grammar(prom: FakePrometheus) -> None:
    now = [T0 + 60]
    poller = AlertPoller(Prometheus(prom.url), known=lambda key: False, clock=lambda: now[0])
    prom.alerts = rf_alerts()
    poller.poll()
    now[0] += 90
    [bundle] = poller.poll()
    lines = render(bundle).split("\n")

    assert re.fullmatch(r"\[경보\] ETCH-02 / CH-A / Lot \S+ / Wafer \S+-W01 / RCP-OX-ETCH-EDU-01", lines[0])
    alert_lines = [line for line in lines if re.match(r"- \d\d:\d\d:\d\d ", line)]
    assert alert_lines == [
        "- 15:15:11 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)",
        "- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.42 W (한계 37 W) (OCAP-ETCH-RF)",
    ]
    sensor_header = lines.index(next(line for line in lines if line.startswith("[센서]")))
    assert re.fullmatch(r"\[센서\] 2026-10-22 15:14:16~\d\d:\d\d:\d\d KST, 5초 간격", lines[sensor_header])
    sensor_lines = lines[sensor_header + 1:]
    assert [line.split(" ")[1] for line in sensor_lines] == ["gas_sf6_pv_sccm", "source_rf_reflected_w"]
    for line, series in zip(sensor_lines, bundle.sensor_data, strict=True):
        assert re.match(r"- \S+ \(\S+, 정상 \d+\.\d{3}±\d+\.\d{3}\): ", line)
        values = line.split(": ", 1)[1].split(" ")
        assert len(values) == len(series.points) == 26  # 125 s window at 5 s
        assert values[2] == "-"  # a missing sample stays visible
    assert summary(bundle) == "ETCH-02/CH-A SIMLOT-20261022-2A151416 경보 2건: FDC_WATCH, RF_REFLECT_HIGH"


def test_submit_creates_one_system_task_and_sends_role_system(
    client: TestClient, wire: Wire, prom: FakePrometheus
) -> None:
    now = [T0 + 60]
    poller = AlertPoller(Prometheus(prom.url), known=lambda key: False, clock=lambda: now[0])
    prom.alerts = rf_alerts()
    poller.poll()
    now[0] += 90
    [bundle] = poller.poll()
    store, settings = client.app.state.store, client.app.state.settings

    # When the closed bundle is submitted twice.
    tid = anyio.run(submit, store, settings, bundle)
    assert anyio.run(submit, store, settings, bundle) is None

    # Then exactly one task exists, attributed to the system requester, and the agent got role=system text.
    assert tid is not None and store.alert_known(bundle.key)
    path, headers, body = wire.commands.get_nowait()
    assert wire.commands.empty()
    assert path == f"/internal/tasks/{tid}/run"
    assert body == {"role": "system", "content": render(bundle)}
    assert headers["X-Requester-Name"] == "FAB-ALERT" and headers["X-Requester-Role"] == "user"
    task = detail(client, str(tid))
    assert task.user_name == "FAB-ALERT" and task.question == summary(bundle)
    assert task.messages[0].text == render(bundle)
