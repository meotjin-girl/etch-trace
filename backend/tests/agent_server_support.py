"""A real HTTP Agent Server boundary and a fixed-time alert bundle."""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from threading import Thread
from typing import override
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue, TypeAdapter
from v1_alerts import AlertBundle, AlertItem, SensorSeries, Window


@dataclass
class AgentWire:
    """Mutable fixture controls HTTP responses and records received requests."""

    commands: Queue[tuple[str, dict[str, str], dict[str, JsonValue]]] = field(default_factory=Queue)
    thread_id: UUID = field(default_factory=uuid4)
    create_status: int = 200
    run_status: int = 200
    url: str = ""


@pytest.fixture
def agent_wire() -> Iterator[AgentWire]:
    state = AgentWire()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = TypeAdapter(dict[str, JsonValue]).validate_json(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            state.commands.put(
                (self.path, {key.lower(): value for key, value in self.headers.items()}, body)
            )
            creating = self.path.endswith("/threads")
            self.send_response(state.create_status if creating else state.run_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            _ = self.wfile.write(json.dumps({"thread_id": str(state.thread_id)}).encode())

        @override
        def log_message(self, format: str, *args: str) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_port}/agent"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def bundle() -> AlertBundle:
    moment = datetime(2026, 10, 23, 1, 0, tzinfo=UTC)
    return AlertBundle(
        key="ETCH-02/CH-A/LOT-1",
        tool_id="ETCH-02",
        chamber_id="CH-A",
        lot_id="LOT-1",
        wafer_id="W01",
        recipe_id="RCP-1",
        window=Window(start=moment, end=moment, step_s=5),
        alerts=[
            AlertItem(
                source="equipment",
                rule="RF_REFLECT_HIGH",
                sensor="source_rf_reflected_w",
                ocap_ref="OCAP-ETCH-RF",
                started_at=moment,
                value=39.42,
                value_meaning="Sensor value",
                limit=37,
                unit="W",
            )
        ],
        sensor_data=[
            SensorSeries(
                sensor="source_rf_reflected_w",
                unit="W",
                subsystem="rf",
                normal_mean=5.364,
                normal_sd=0.59,
                points=[(moment, 39.42)],
            )
        ],
    )
