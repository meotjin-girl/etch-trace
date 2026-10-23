"""Real HTTP submission and lifespan routing for the optional Agent Server."""

from threading import Event

import anyio
import httpx2
import main
import pytest
from agent_server_alerts import submit
from agent_server_support import AgentWire, agent_wire, bundle
from conftest import Wire, headers, settings
from fastapi.testclient import TestClient
from v1_alerts import render
from v1_models import Settings
from v1_store import Store

__all__ = ["agent_wire"]


def test_submit_creates_thread_and_run_without_legacy_task(
    client: TestClient, agent_wire: AgentWire, wire: Wire
) -> None:
    # Given a closed alert and a separately configured Agent Server.
    alert = bundle()
    config = settings("", wire, agent_server_url=agent_wire.url)
    # When the alert is submitted across the real HTTP boundary.
    thread_id = anyio.run(submit, config, alert)
    # Then both requests use internal authentication and the exact request envelope.
    assert thread_id == agent_wire.thread_id
    path, request_headers, body = agent_wire.commands.get_nowait()
    assert path == "/agent/threads" and body == {}
    assert request_headers["x-internal-key"] == "test-key"
    path, request_headers, body = agent_wire.commands.get_nowait()
    assert path == f"/agent/threads/{thread_id}/runs"
    assert request_headers["x-internal-key"] == "test-key"
    assert "authorization" not in request_headers
    assert body == {
        "assistant_id": "trace",
        "input": {"request": {"role": "system", "content": render(alert)}},
        "multitask_strategy": "reject",
    }
    assert agent_wire.commands.empty()
    assert client.get("/api/ai/tasks", headers=headers()).json() == []


@pytest.mark.parametrize("failure_stage", ["thread", "run"])
def test_failed_submit_is_not_retried(agent_wire: AgentWire, failure_stage: str) -> None:
    # Given a failing remote operation.
    agent_wire.create_status = 503 if failure_stage == "thread" else 200
    agent_wire.run_status = 503
    config = Settings("", "", "test-key", agent_server_url=agent_wire.url)
    # When submission reaches that operation.
    with pytest.raises(httpx2.HTTPStatusError):
        _ = anyio.run(submit, config, bundle())
    # Then it fails visibly without retrying creation or run submission.
    assert agent_wire.commands.qsize() == (1 if failure_stage == "thread" else 2)


@pytest.mark.parametrize("agent_url", ["", "http://agent-server:2024"])
def test_environment_selects_new_or_legacy_watcher(
    database_url: str, monkeypatch: pytest.MonkeyPatch, agent_url: str
) -> None:
    # Given a configured poller and event-signaling watcher boundaries.
    new_started, legacy_started = Event(), Event()

    async def new_watch(config: Settings) -> None:
        assert config.agent_server_url == agent_url
        new_started.set()
        await anyio.sleep_forever()

    async def legacy_watch(_store: Store, config: Settings) -> None:
        assert config.agent_server_url == ""
        legacy_started.set()
        await anyio.sleep_forever()

    monkeypatch.setattr(main, "watch_agent_server_alerts", new_watch)
    monkeypatch.setattr(main, "watch_alerts", legacy_watch)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key")
    monkeypatch.setenv("PROMETHEUS_URL", "http://prometheus:9090")
    monkeypatch.setenv("AGENT_SERVER_URL", agent_url)
    # When the actual environment-based lifespan starts.
    with TestClient(main.create_app()):
        # Then exactly the chosen watcher starts; the event is subscribed before startup.
        selected = new_started if agent_url else legacy_started
        assert selected.wait(timeout=5)
        assert new_started.is_set() == bool(agent_url)
        assert legacy_started.is_set() != bool(agent_url)
