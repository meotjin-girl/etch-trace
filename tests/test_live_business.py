"""Exercise live investigation MCP tools through the real HTTP boundary."""

import json
import sys
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import override
from uuid import uuid4

import anyio
import pytest
from fastmcp import Client
from pydantic import JsonValue, TypeAdapter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import business


@pytest.fixture
def live_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, JsonValue]]]:
    requests: list[dict[str, JsonValue]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self) -> None:
            payload = TypeAdapter(dict[str, JsonValue]).validate_json(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            requests.append(
                {
                    "method": "PUT",
                    "path": self.path,
                    "key": self.headers.get("X-Internal-Key"),
                    "payload": payload,
                }
            )
            self.reply({"id": self.path.rsplit("/", 1)[-1], "revision": 1})

        def do_GET(self) -> None:
            requests.append(
                {
                    "method": "GET",
                    "path": self.path,
                    "key": self.headers.get("X-Internal-Key"),
                }
            )
            self.reply({"summary": "저장된 분석", "approval": None})

        def reply(self, payload: dict[str, JsonValue]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            _ = self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: str | int) -> None:
            return

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        monkeypatch.setenv("BACKEND_URL", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("INTERNAL_API_KEY", "test-internal")
        try:
            yield requests
        finally:
            server.shutdown()
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_publication_forwards_thread_payload_and_internal_key(
    live_backend: list[dict[str, JsonValue]],
) -> None:
    # Given: a real FastMCP client and HTTP backend.
    thread_id = str(uuid4())
    payload: dict[str, JsonValue] = {
        "base_revision": 0,
        "summary": "새 원인 후보",
        "candidates": [],
    }

    async def publish() -> None:
        async with Client(business.mcp) as client:
            result = await client.call_tool(
                "upsert_live_investigation",
                {"thread_id": thread_id, "payload": payload},
            )
            assert not result.is_error

    # When: publishing through the actual tool schema and transport.
    anyio.run(publish)
    # Then: the backend receives the exact business request, not a legacy DONE.
    assert live_backend == [
        {
            "method": "PUT",
            "path": f"/internal/investigations/live/{thread_id}",
            "key": "test-internal",
            "payload": payload,
        }
    ]


def test_read_returns_backend_approval_instead_of_model_state(
    live_backend: list[dict[str, JsonValue]],
) -> None:
    # Given: a real backend whose approval is authoritative.
    thread_id = str(uuid4())

    async def read_record() -> None:
        async with Client(business.mcp) as client:
            # When: reading the persisted record through MCP.
            result = await client.call_tool("get_live_investigation", {"thread_id": thread_id})
            # Then: the returned data is the backend's record.
            assert result.structured_content == {"summary": "저장된 분석", "approval": None}

    anyio.run(read_record)
    assert live_backend == [
        {
            "method": "GET",
            "path": f"/internal/investigations/live/{thread_id}",
            "key": "test-internal",
        }
    ]
