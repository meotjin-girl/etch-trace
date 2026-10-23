"""Prometheus alert intake: bundle firing alerts per (tool, chamber, lot) into agent system requests.

Format and rules: docs/agent-request.md.
"""

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from http.client import HTTPResponse
from typing import TypedDict, cast, final
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import UUID

import anyio
from pydantic import BaseModel
from v1_dispatch import dispatch
from v1_models import Settings
from v1_store import Store

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))
POLL_S = 5
STEP_S = 5
RUN_S = 125  # one mock run: 25 samples + the next run's first sample
CLOSE_AFTER_S = 90
FDC_VALUE = {
    "FDC_WATCH": "z={:.1f}",
    "PRESSURE_TREND": "예측={:.1f} mTorr",
    "PRESSURE_OSC": "σ40s={:.2f}",
    "SENSOR_STALE": "변화={:g}",
    "MULTIVARIATE_FDC": "계통={:g}",
}
FDC_MEANING = {
    "FDC_WATCH": "z-score",
    "PRESSURE_TREND": "60초 후 예측 압력",
    "PRESSURE_OSC": "40초 표준편차",
    "SENSOR_STALE": "20초 변화 횟수",
    "MULTIVARIATE_FDC": "이탈 계통 수",
}


class PromAlert(TypedDict):
    labels: dict[str, str]
    state: str
    activeAt: str
    value: str


class Sample(TypedDict):
    metric: dict[str, str]
    value: tuple[float, str]


class Series(TypedDict):
    metric: dict[str, str]
    values: list[tuple[float, str]]


class AlertItem(BaseModel):
    source: str
    rule: str
    sensor: str | None
    ocap_ref: str | None
    started_at: datetime
    value: float | None
    value_meaning: str
    limit: float | None = None
    unit: str | None = None


class SensorSeries(BaseModel):
    sensor: str
    unit: str
    subsystem: str
    normal_mean: float | None
    normal_sd: float | None
    points: list[tuple[datetime, float | None]]


class Window(BaseModel):
    start: datetime
    end: datetime
    step_s: int


class AlertBundle(BaseModel):
    key: str
    tool_id: str
    chamber_id: str
    lot_id: str
    wafer_id: str | None
    recipe_id: str | None
    window: Window
    alerts: list[AlertItem]
    sensor_data: list[SensorSeries]


def parse_time(text: str) -> datetime:
    """Prometheus RFC3339 with up to nanoseconds -> aware datetime."""
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", text))


def num(value: float | None) -> str:
    return "-" if value is None else f"{round(value, 3):g}"


@final
class Prometheus:
    def __init__(self, url: str, timeout: float = 5):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, **params: str | float) -> dict[str, object]:
        url = f"{self.url}{path}?{urlencode(params)}"
        with cast(HTTPResponse, urlopen(url, timeout=self.timeout)) as response:
            body = cast(dict[str, object], json.load(response))
        if body.get("status") != "success":
            raise RuntimeError(f"Prometheus {path} failed: {body.get('error')}")
        return cast(dict[str, object], body["data"])

    def alerts(self) -> list[PromAlert]:
        return cast(list[PromAlert], self.get("/api/v1/alerts")["alerts"])

    def instant(self, query: str, at: datetime | None = None) -> list[Sample]:
        params: dict[str, str | float] = {"query": query}
        if at is not None:
            params["time"] = at.timestamp()
        return cast(list[Sample], self.get("/api/v1/query", **params)["result"])

    def series(self, query: str, start: datetime, end: datetime) -> list[Series]:
        result = self.get(
            "/api/v1/query_range", query=query, start=start.timestamp(), end=end.timestamp(), step=STEP_S
        )["result"]
        return cast(list[Series], result)


def selector(**labels: str) -> str:
    return "{" + ",".join(f"{key}={json.dumps(value)}" for key, value in labels.items()) + "}"


@dataclass
class Bundle:
    key: str
    run: dict[str, str]  # etch_run_info labels at the first alert
    run_start: datetime
    first_seen: float
    alerts: dict[str, PromAlert] = field(default_factory=dict)


@final
class AlertPoller:
    """Pure-ish state machine around Prometheus; returns closed bundles as JSON-able dicts."""

    def __init__(
        self,
        prometheus: Prometheus,
        known: Callable[[str], bool],
        close_after: float = CLOSE_AFTER_S,
        clock: Callable[[], float] = time.time,
    ):
        self.prom = prometheus
        self.known = known
        self.close_after = close_after
        self.clock = clock
        self.open: dict[str, Bundle] = {}
        self.done: set[str] = set()
        self.seen: dict[str, str | None] = {}  # alert fingerprint -> bundle key (None: no run found)

    def poll(self) -> list[AlertBundle]:
        now = self.clock()
        seen: dict[str, str | None] = {}
        for alert in self.prom.alerts():
            labels = alert["labels"]
            if alert["state"] != "firing" or "tool" not in labels or "chamber" not in labels:
                continue
            fingerprint = json.dumps([sorted(labels.items()), alert["activeAt"]])
            key = seen[fingerprint] = self.seen[fingerprint] if fingerprint in self.seen else self.locate(alert, now)
            if key in self.open:
                _ = self.open[key].alerts.setdefault(fingerprint, alert)
        self.seen = seen  # forget alerts that stopped firing

        closed: list[AlertBundle] = []
        for key, bundle in list(self.open.items()):
            current = self.run_info(bundle.run["tool"], bundle.run["chamber"])
            if now - bundle.first_seen >= self.close_after or not current or current["lot_id"] != bundle.run["lot_id"]:
                closed.append(self.build(bundle, now))  # build first: a failed query keeps the bundle open
                del self.open[key]
                self.done.add(key)
        return closed

    def locate(self, alert: PromAlert, now: float) -> str | None:
        labels = alert["labels"]
        active_at = parse_time(alert["activeAt"])
        run = self.run_info(labels["tool"], labels["chamber"], active_at)
        if run is None:
            log.warning("no etch_run_info for %s/%s at %s", labels["tool"], labels["chamber"], active_at)
            return None
        key = f"{run['tool']}/{run['chamber']}/{run['lot_id']}"
        if key not in self.open and key not in self.done:
            if self.known(key):
                self.done.add(key)
            else:
                offset = self.prom.instant(
                    f"etch_sample_offset_seconds{selector(tool=run['tool'], chamber=run['chamber'])}", active_at
                )
                seconds = float(offset[0]["value"][1]) if offset else 0.0
                self.open[key] = Bundle(key, run, active_at - timedelta(seconds=seconds), now)
        return key

    def run_info(self, tool: str, chamber: str, at: datetime | None = None) -> dict[str, str] | None:
        result = self.prom.instant(f"etch_run_info{selector(tool=tool, chamber=chamber)}", at)
        return result[0]["metric"] if result else None

    def build(self, bundle: Bundle, now: float) -> AlertBundle:
        tool, chamber = bundle.run["tool"], bundle.run["chamber"]
        start = bundle.run_start.replace(microsecond=0)
        end = min(datetime.fromtimestamp(now, UTC), start + timedelta(seconds=RUN_S))
        grid = [start + timedelta(seconds=s) for s in range(0, int((end - start).total_seconds()) + 1, STEP_S)]

        labels: dict[str, dict[str, str]] = {}
        stats: dict[tuple[str, str], float] = {}
        for kind in ("mean", "sd"):
            for row in self.prom.instant(f"etch_sensor_normal_{kind}", end):
                labels[row["metric"]["sensor"]] = row["metric"]
                stats[row["metric"]["sensor"], kind] = float(row["value"][1])

        sensor_data: list[SensorSeries] = []
        query = f'etch_sensor_value{selector(tool=tool, chamber=chamber)[:-1]},sensor!="plasma_detected"}}'
        for row in sorted(self.prom.series(query, start, end), key=lambda r: r["metric"]["sensor"]):
            name = row["metric"]["sensor"]
            values = {round(float(t)): float(v) for t, v in row["values"]}
            meta = labels.get(name, {})
            sensor_data.append(SensorSeries(
                sensor=name,
                unit=meta.get("unit", ""),
                subsystem=meta.get("subsystem", ""),
                normal_mean=stats.get((name, "mean")),
                normal_sd=stats.get((name, "sd")),
                points=[(t, values.get(round(t.timestamp()))) for t in grid],
            ))

        alerts: list[AlertItem] = []
        for alert in sorted(bundle.alerts.values(), key=lambda a: parse_time(a["activeAt"])):
            tags = alert["labels"]
            active_at = parse_time(alert["activeAt"])
            if tags["alertname"] == "EQUIPMENT_ALARM":
                # the alert value is the 0/1 flag; report the sensor reading at that moment instead
                sensor = tags.get("sensor", "")
                reading = self.prom.instant(
                    f"etch_sensor_value{selector(tool=tool, chamber=chamber, sensor=sensor)}", active_at
                )
                item = AlertItem(
                    source="equipment", rule=tags["alarm"], sensor=sensor or None, ocap_ref=tags.get("ocap"),
                    started_at=active_at, value=float(reading[0]["value"][1]) if reading else None,
                    value_meaning="센서값", limit=float(tags["limit"]) if "limit" in tags else None,
                    unit=labels.get(sensor, {}).get("unit"),
                )
            else:
                item = AlertItem(
                    source=tags.get("source", "fdc"), rule=tags["alertname"], sensor=tags.get("sensor"),
                    ocap_ref=tags.get("ocap"), started_at=active_at, value=float(alert["value"]),
                    value_meaning=FDC_MEANING.get(tags["alertname"], "값"),
                )
            alerts.append(item)

        return AlertBundle(
            key=bundle.key, tool_id=tool, chamber_id=chamber, lot_id=bundle.run["lot_id"],
            wafer_id=bundle.run.get("wafer_id"), recipe_id=bundle.run.get("recipe_id"),
            window=Window(start=start, end=end, step_s=STEP_S), alerts=alerts, sensor_data=sensor_data,
        )


def render(bundle: AlertBundle) -> str:
    """Fixed-format text sent as content of a role=system request (docs/agent-request.md)."""

    def clock(moment: datetime) -> str:
        return moment.astimezone(KST).strftime("%H:%M:%S")

    header = (
        f"[경보] {bundle.tool_id} / {bundle.chamber_id} / Lot {bundle.lot_id} / "
        f"Wafer {bundle.wafer_id} / {bundle.recipe_id}"
    )
    lines = [header]
    for alert in bundle.alerts:
        sensor = alert.sensor or "-"
        if alert.source == "equipment":
            unit = alert.unit or ""
            value = f"{sensor}={num(alert.value)} {unit} (한계 {num(alert.limit)} {unit})"
            source = "장비"
        else:
            pattern = FDC_VALUE.get(alert.rule, "값={:g}")
            value = f"{sensor} {pattern.format(alert.value)}"
            source = "FDC"
        lines.append(f"- {clock(alert.started_at)} {source} {alert.rule} {value} ({alert.ocap_ref})")
    window = bundle.window
    start = window.start.astimezone(KST)
    lines.append(f"[센서] {start:%Y-%m-%d %H:%M:%S}~{clock(window.end)} KST, {window.step_s}초 간격")
    for series in bundle.sensor_data:
        mean, sd = series.normal_mean, series.normal_sd
        normal = f"정상 {mean:.3f}±{sd:.3f}" if mean is not None and sd is not None else "정상 -"
        values = " ".join(num(value) for _, value in series.points)
        lines.append(f"- {series.sensor} ({series.unit}, {normal}): {values}")
    return "\n".join(lines)


def summary(bundle: AlertBundle) -> str:
    rules = list(dict.fromkeys(alert.rule for alert in bundle.alerts))
    return f"{bundle.tool_id}/{bundle.chamber_id} {bundle.lot_id} 경보 {len(bundle.alerts)}건: {', '.join(rules)}"


async def submit(store: Store, settings: Settings, bundle: AlertBundle) -> UUID | None:
    content = render(bundle)
    evidence = bundle.model_dump(mode="json")
    tid = await anyio.to_thread.run_sync(store.create_alert_task, summary(bundle), evidence, content)
    if tid is not None:
        await dispatch(store, settings, tid, {"role": "system", "content": content})
    return tid


async def watch(store: Store, settings: Settings) -> None:
    poller = AlertPoller(Prometheus(settings.prometheus_url), store.alert_known)
    while True:
        try:
            for bundle in await anyio.to_thread.run_sync(poller.poll):
                log.info("alert bundle closed: %s (%d alerts)", bundle.key, len(bundle.alerts))
                _ = await submit(store, settings, bundle)
        except Exception:  # Prometheus or DB hiccup: keep polling, open bundles stay open
            log.exception("alert poll failed")
        await anyio.sleep(POLL_S)
