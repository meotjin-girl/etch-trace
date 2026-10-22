"""SECS/GEM host for the mock tools; serves current values as a page, JSON and Prometheus metrics."""

import datetime
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import secsgem.common
import secsgem.gem
import secsgem.hsms
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.core import GaugeMetricFamily

import sensors

log = logging.getLogger("collector")
EVENTS_ENABLED_SVID, ALARMS_SET_SVID = 1003, 1005  # secsgem built-ins
NAMES = list(sensors.SVID_OFFSET)
ALARM_NAMES = list(sensors.ALARMS)
RECONNECT_AFTER = 6  # failed polls (30 s)


class Link:
    """One HSMS host connection to one tool, polled every SAMPLE_S."""

    def __init__(self, tool_id: str, address: str, port: int):
        self.tool_id = tool_id
        self.up = False
        self.updated_at: str | None = None
        self.chambers: dict[str, dict] = {c: {} for c in sensors.CHAMBER_BAND}
        self.alarms: set[int] = set()
        self.svids = [band + off for band in sensors.CHAMBER_BAND.values() for off in sensors.SVID_OFFSET.values()]
        self.ceids = {band + c for band in sensors.CHAMBER_BAND.values() for c in (sensors.CEID_RUN_START, sensors.CEID_RUN_END)}
        self.host = secsgem.gem.GemHostHandler(
            secsgem.hsms.HsmsSettings(
                address=address,
                port=port,
                connect_mode=secsgem.hsms.HsmsConnectMode.ACTIVE,
                device_type=secsgem.common.DeviceType.HOST,
            )
        )
        self.host.events.alarm_received += self._on_alarm
        self.host.events.collection_event_received += self._on_event

    def _on_alarm(self, data):
        state = "SET" if data["code"].get() & 0x80 else "CLEAR"
        log.info("%s S5F1 %s %s", self.tool_id, state, data["text"].get())

    def _on_event(self, data):
        values = {v["dvid"]: v["value"] for v in data["values"]}
        log.info("%s S6F11 ceid=%s %s", self.tool_id, data["ceid"].get(), values)

    def _subscribe(self):
        self.host.clear_collection_events()
        for band in sensors.CHAMBER_BAND.values():
            context = [band + sensors.SVID_OFFSET[n] for n in sensors.CONTEXT]
            for ceid in (sensors.CEID_RUN_START, sensors.CEID_RUN_END):
                self.host.subscribe_collection_event(band + ceid, context)

    def poll(self) -> None:
        # ponytail: S1F3 polling instead of S2F23/S6F1 trace (not implemented in secsgem 0.3.0)
        if not self.host.waitfor_communicating(1):  # sending before S1F13 completes blocks for T3 (45 s)
            self.up = False
            return
        reply = None
        try:
            request = self.host.stream_function(1, 3)([*self.svids, EVENTS_ENABLED_SVID, ALARMS_SET_SVID])
            reply = self.host.send_and_waitfor_response(request)
            *values, events, alarms = self.host.settings.streams_functions.decode(reply).get()
        except Exception:
            log.warning("%s poll failed, reply=%s", self.tool_id, reply and reply.header, exc_info=True)
            self.up = False
            return
        for i, chamber in enumerate(sensors.CHAMBER_BAND):
            self.chambers[chamber] = dict(zip(NAMES, values[i * len(NAMES) : (i + 1) * len(NAMES)]))
        self.alarms = set(alarms)
        self.up = True
        self.updated_at = datetime.datetime.now(datetime.UTC).isoformat()
        if not self.ceids <= set(events):  # a restarted tool forgets reports; the enabled list says so
            try:
                self._subscribe()
            except Exception:
                log.warning("%s subscribe failed", self.tool_id, exc_info=True)

    def run(self) -> None:
        self.host.enable()
        failures = 0
        while True:
            started = time.monotonic()
            self.poll()
            failures = 0 if self.up else failures + 1
            if failures >= RECONNECT_AFTER:
                # secsgem can wedge when both sides start together; rebuild the link instead of waiting forever
                log.warning("%s no reply for %d polls, reconnecting", self.tool_id, failures)
                self.host.disable()
                self.host.enable()
                failures = 0
            time.sleep(max(0.0, sensors.SAMPLE_S - (time.monotonic() - started)))

    def active_alarms(self, chamber: str) -> list[dict]:
        base = sensors.CHAMBER_BAND[chamber] + sensors.ALID_OFFSET
        return [
            {"alarm": name, "ocap": sensors.ALARMS[name][3]}
            for i, name in enumerate(ALARM_NAMES)
            if base + i in self.alarms
        ]


def snapshot(links: list[Link]) -> dict:
    sensor_meta = {
        name: {"mean": m, "sd": sd, "low": round(m - 3 * sd, 3), "high": round(m + 3 * sd, 3), "subsystem": sub, "unit": unit}
        for name, (m, sd, _, sub, unit, _) in sensors.SENSORS.items()
    }
    modules = [
        {
            "tool": link.tool_id,
            "chamber": chamber,
            "up": link.up,
            "updated_at": link.updated_at,
            "context": {k: values.get(k) for k in sensors.CONTEXT},
            "setpoints": {k: values.get(k) for k in sensors.SETPOINTS},
            "values": {k: values.get(k) for k in (*sensors.SENSORS, *sensors.FLAGS)},
            "alarms": link.active_alarms(chamber) if link.up else [],
        }
        for link in links
        for chamber, values in link.chambers.items()
    ]
    return {
        "synthetic": True,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "sensors": sensor_meta,
        "modules": modules,
    }


class Metrics:
    """Builds metrics from current state at scrape time, so finished runs leave no stale series."""

    def __init__(self, links: list[Link]):
        self.links = links

    def collect(self):
        def gauge(name, doc, labels):
            return GaugeMetricFamily(name, doc, labels=labels)

        value = gauge("etch_sensor_value", "Synthetic sensor readback", ["tool", "chamber", "sensor"])
        setpoint = gauge("etch_setpoint", "Recipe setpoint", ["tool", "chamber", "sensor"])
        quality = gauge("etch_data_quality_good", "1 when sensor_data_quality is GOOD", ["tool", "chamber"])
        offset = gauge("etch_sample_offset_seconds", "Seconds into the current run", ["tool", "chamber"])
        info = gauge("etch_run_info", "Current run context", ["tool", "chamber", "lot_id", "wafer_id", "recipe_id", "run_no"])
        alarm = gauge("etch_alarm_active", "Equipment S5F1 alarm state", ["tool", "chamber", "alarm", "ocap"])
        up = gauge("etch_equipment_up", "HSMS link communicating", ["tool"])
        mean = gauge("etch_sensor_normal_mean", "Normal-lot mean", ["sensor", "subsystem", "unit", "ocap"])
        sd = gauge("etch_sensor_normal_sd", "Normal-lot standard deviation", ["sensor", "subsystem", "unit", "ocap"])
        for name, (m, s, _, sub, unit, ocap) in sensors.SENSORS.items():
            mean.add_metric([name, sub, unit, ocap], m)
            sd.add_metric([name, sub, unit, ocap], s)

        for link in self.links:
            up.add_metric([link.tool_id], int(link.up))
            if not link.up:
                continue
            for chamber, v in link.chambers.items():
                if not v:
                    continue
                ids = [link.tool_id, chamber]
                for name in (*sensors.SENSORS, "plasma_detected"):
                    value.add_metric([*ids, name], v[name])
                for name in sensors.SETPOINTS:
                    setpoint.add_metric([*ids, name], v[name])
                quality.add_metric(ids, int(v["sensor_data_quality"] == "GOOD"))
                offset.add_metric(ids, v["sample_offset_s"])
                info.add_metric([*ids, v["lot_id"], v["wafer_id"], v["recipe_id"], str(v["run_no"])], 1)
                active = {a["alarm"] for a in link.active_alarms(chamber)}
                for name, (*_, ocap) in sensors.ALARMS.items():
                    alarm.add_metric([*ids, name, ocap], int(name in active))
        yield from (value, setpoint, quality, offset, info, alarm, up, mean, sd)


def serve(links: list[Link], port: int) -> ThreadingHTTPServer:
    registry = CollectorRegistry()
    registry.register(Metrics(links))
    page = (Path(__file__).parent / "index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                self._send(200, "text/html; charset=utf-8", page)
            elif path == "/api/current":
                self._send(200, "application/json", json.dumps(snapshot(links)).encode())
            elif path == "/metrics":
                self._send(200, CONTENT_TYPE_LATEST, generate_latest(registry))
            else:
                self._send(404, "text/plain", b"not found")

        def _send(self, status, content_type, body):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("secsgem").setLevel(logging.WARNING)
    logging.getLogger("communication").setLevel(logging.WARNING)
    links = []
    for entry in os.getenv("EQUIPMENT", "ETCH-01=etch-01:5000,ETCH-02=etch-02:5000,ETCH-03=etch-03:5000").split(","):
        tool_id, address = entry.split("=")
        host, port = address.split(":")
        links.append(Link(tool_id, host, int(port)))
    for link in links:
        threading.Thread(target=link.run, daemon=True, name=link.tool_id).start()
    serve(links, int(os.getenv("HTTP_PORT", "8080")))
    threading.Event().wait()


if __name__ == "__main__":
    main()
