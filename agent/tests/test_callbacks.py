import json
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph import build_graph
from agent.main import Callback, create_app
from agent.tests.support import Evidence


@pytest.fixture
def receiver():
    received = []
    guard = Lock()
    response_status = [200]

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with guard:
                received.append((self.path, dict(self.headers), body))
            self.send_response(response_status[0])
            self.end_headers()

        def log_message(self, format, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", received, response_status
        finally:
            server.shutdown()
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_callbacks_when_tasks_run_concurrently_keep_command_headers_isolated(receiver, monkeypatch):
    # Given: HTTP callbacks and simultaneous real graph invocations.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    url, received, _ = receiver
    app = create_app()
    app.state.internal_key = "internal"
    app.state.graph = build_graph(InMemorySaver(), Evidence(), Callback(url, "internal"))
    tasks = [str(uuid4()), str(uuid4())]
    commands = {task: str(uuid4()) for task in tasks}

    # Do not enter TestClient lifespan: the graph is explicitly injected.
    def without_lifespan(task):
        client = TestClient(app)
        return client.post(
            f"/internal/tasks/{task}/run",
            headers={"X-Internal-Key": "internal", "X-Command-ID": commands[task]},
            json={"question": "ETCH-07 endpoint 지연 94초"},
        )

    # When
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(without_lifespan, tasks))
    # Then
    assert all(response.status_code == 200 for response in responses)
    assert len(received) == 8
    for path, headers, event in received:
        task = path.split("/")[3]
        assert headers["X-Command-Id"] == commands[task]
        assert headers["X-Internal-Key"] == "internal"
        assert event["event_id"]
        assert event["type"] in {
            "SEARCH_STARTED", "ANALYSIS_STARTED", "REPORT_STARTED", "APPROVAL_REQUIRED",
        }


def test_callback_failure_when_backend_rejects_is_visible_as_http_failure(receiver, monkeypatch):
    # Given
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    url, received, status = receiver
    status[0] = 503
    app = create_app()
    app.state.internal_key = "internal"
    app.state.graph = build_graph(InMemorySaver(), Evidence(), Callback(url, "internal"))
    client = TestClient(app, raise_server_exceptions=False)
    # When
    response = client.post(
        f"/internal/tasks/{uuid4()}/run",
        headers={"X-Internal-Key": "internal", "X-Command-ID": str(uuid4())},
        json={"question": "ETCH-07 endpoint 지연"},
    )
    # Then
    assert response.status_code == 500
    assert len(received) == 1
