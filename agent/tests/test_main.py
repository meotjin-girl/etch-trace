from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph import build_graph
from agent.main import create_app
from agent.tests.support import Events, Evidence


@pytest.fixture
def api(monkeypatch):
    # The public HTTP handler runs a real graph; only evidence and persistence are local.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app()
    events = Events()
    app.state.graph = build_graph(InMemorySaver(), Evidence(), events)
    app.state.internal_key = "test-key"
    return TestClient(app, headers={"X-Command-ID": str(uuid4())}), events


def test_internal_key_when_missing_or_wrong_is_rejected(api):
    # Given
    client, events = api
    url = f"/internal/tasks/{uuid4()}/run"
    # When / Then
    assert client.post(url, json={"question": "ETCH-07 endpoint 지연"}).status_code == 403
    assert client.post(url, headers={"X-Internal-Key": "wrong"},
                       json={"question": "ETCH-07 endpoint 지연"}).status_code == 403
    assert not events.values


def test_http_flow_when_clarifying_revising_then_approving(api):
    # Given
    client, events = api
    url = f"/internal/tasks/{uuid4()}/run"
    headers = {"X-Internal-Key": "test-key"}
    initial = client.post(url, headers=headers, json={"question": "endpoint 지연 94초"})
    assert initial.json() == {"status": "interrupted", "waiting": "clarification"}
    assert client.post(url, headers=headers, json={
        "resume": {"action": "approve", "comment": "", "by": "engineer"},
    }).status_code == 409
    clarified = client.post(url, headers=headers, json={"resume": {"text": "ETCH-07"}})
    assert clarified.json()["waiting"] == "review"
    revised = client.post(url, headers=headers, json={
        "resume": {"action": "revise", "comment": "근거 보완 요청", "by": "engineer"},
    })
    assert revised.json()["waiting"] == "review"
    # When
    approved = client.post(url, headers=headers, json={
        "resume": {"action": "approve", "comment": "", "by": "engineer"},
    })
    # Then
    assert approved.json() == {"status": "completed"}
    assert events.values[-1].payload["report"]["feedback"] == ["근거 보완 요청"]
    assert client.post(url, headers=headers, json={
        "resume": {"action": "approve", "comment": "", "by": "engineer"},
    }).status_code == 409
    assert client.post(url, headers=headers, json={"question": "새 조사"}).status_code == 409


@pytest.mark.parametrize("payload", [
    {},
    {"question": "x", "resume": {"text": "x"}},
    {"resume": {"text": "x", "action": "approve", "comment": "", "by": "x"}},
    {"resume": {"action": "save", "comment": "", "by": "x"}},
    {"resume": {"action": "approve", "comment": ""}},
])
def test_payload_when_not_one_valid_command_is_rejected(api, payload):
    # Given
    client, events = api
    # When
    response = client.post(f"/internal/tasks/{uuid4()}/run",
                           headers={"X-Internal-Key": "test-key"}, json=payload)
    # Then
    assert response.status_code == 422
    assert not events.values
