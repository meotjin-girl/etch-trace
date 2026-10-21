"""Wire payloads, scoped event IDs and invalid transition boundaries."""

import pytest
from conftest import API, KEY, Wire, detail, event, headers, task
from fastapi.testclient import TestClient


def test_initial_dispatch_uses_simple_body_and_command_header(
    client: TestClient,
    wire: Wire,
) -> None:
    # Given the agent HTTP boundary.
    # When an initial task is accepted.
    tid = task(client)
    # Then the accepted command identity is forwarded without changing its body.
    path, request_headers, body = wire.commands.get_nowait()
    assert path == f"/internal/tasks/{tid}/run"
    assert body == {"question": "Investigate etch"}
    assert request_headers["X-Internal-Key"] == "test-key"
    assert request_headers["X-Command-ID"] == str(detail(client, tid).command_id)
    assert request_headers["X-Requester-Name"] == "owner"
    assert request_headers["X-Requester-Role"] == "user"
    assert "Authorization" not in request_headers


def test_message_dispatch_contains_only_resume_text(client: TestClient, wire: Wire) -> None:
    # Given a task waiting for clarification.
    tid = task(client)
    wire.commands.get_nowait()
    event(client, tid, "QUESTION", {"text": "Chamber?"})
    # When its owner responds.
    response = client.post(f"{API}/{tid}/messages", headers=headers(), json={"text": "CH-A"})
    # Then the agent receives the agreed simple resume shape.
    assert response.status_code == 202
    _, request_headers, body = wire.commands.get_nowait()
    assert body == {"resume": {"text": "CH-A"}}
    assert request_headers["X-Command-ID"] == str(detail(client, tid).command_id)


def test_review_dispatch_derives_actor_and_keeps_metadata_local(
    client: TestClient,
    wire: Wire,
) -> None:
    # Given a task waiting for engineer review.
    tid = task(client)
    wire.commands.get_nowait()
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    # When an engineer requests revision with optional business metadata.
    response = client.post(
        f"{API}/{tid}/approval",
        headers=headers("검토자", "engineer"),
        json={"action": "revise", "comment": "Check RF", "lot_id": "L1"},
    )
    # Then identity is server-derived and only the agreed resume fields reach the agent.
    assert response.status_code == 202
    _, _, body = wire.commands.get_nowait()
    assert body == {"resume": {"action": "revise", "comment": "Check RF", "by": "검토자"}}
    assert detail(client, tid).reviews[0].lot_id == "L1"


def test_reused_event_id_in_new_command_is_not_suppressed(client: TestClient) -> None:
    # Given an event ID used in an earlier suspended command.
    tid = task(client)
    event(client, tid, "QUESTION", {"text": "Chamber?"}, "question")
    client.post(f"{API}/{tid}/messages", headers=headers(), json={"text": "CH-A"})
    # When the agent uses the same local ID in the new command.
    response = event(client, tid, "QUESTION", {"text": "Recipe?"}, "question")
    # Then scope separates the events and preserves their order.
    assert response.json() == {"accepted": True, "duplicate": False}
    data = detail(client, tid)
    assert data.status == "WAITING_INPUT"
    assert len([row for row in data.events if row.type == "QUESTION"]) == 2
    assert [row.seq for row in data.events] == list(range(1, len(data.events) + 1))


def test_conflicting_event_replay_is_rejected(client: TestClient) -> None:
    # Given an acknowledged progress event ID.
    tid = task(client)
    event(client, tid, "SEARCH_STARTED", {"step": 1}, "one")
    # When a caller reuses that ID for different content.
    response = event(client, tid, "SEARCH_STARTED", {"step": 2}, "one")
    # Then the original event is immutable.
    assert response.status_code == 409
    assert len([row for row in detail(client, tid).events if row.type == "SEARCH_STARTED"]) == 1


@pytest.mark.parametrize(
    "suffix,body",
    [
        ("/messages", {"text": "Unexpected response"}),
        ("/approval", {"action": "approve", "comment": ""}),
    ],
)
def test_commands_reject_nonwaiting_tasks(
    client: TestClient,
    suffix: str,
    body: dict[str, str],
) -> None:
    # Given a running task.
    tid = task(client)
    # When a waiting-only command is submitted.
    response = client.post(f"{API}/{tid}{suffix}", headers=headers("owner", "engineer"), json=body)
    # Then state is unchanged.
    assert response.status_code == 409
    assert detail(client, tid).status == "RUNNING"


def test_missing_report_does_not_transition_task(client: TestClient) -> None:
    # Given a running task.
    tid = task(client)
    # When approval is requested without its report.
    response = event(client, tid, "APPROVAL_REQUIRED")
    # Then validation rejects the event and state remains running.
    assert response.status_code == 422
    assert detail(client, tid).status == "RUNNING"


def test_unscoped_callbacks_are_rejected(client: TestClient) -> None:
    # Given a valid service identity but no command scope.
    tid = task(client)
    # When a callback omits command identity.
    response = client.post(
        f"/internal/tasks/{tid}/events",
        headers=KEY,
        json={"event_id": "one", "type": "FAILED", "payload": {}},
    )
    # Then it cannot affect any task state.
    assert response.status_code == 422
    assert detail(client, tid).status == "RUNNING"


def test_rest_event_cursor_returns_only_new_events(client: TestClient) -> None:
    # Given a task with a captured event cursor.
    tid = task(client)
    cursor = detail(client, tid).events[-1].seq
    event(client, tid, "ANALYSIS_STARTED")
    # When using REST fallback to request later events.
    response = client.get(f"{API}/{tid}/events?after={cursor}", headers=headers())
    # Then replay starts strictly after that cursor.
    assert [row["type"] for row in response.json()] == ["ANALYSIS_STARTED"]
