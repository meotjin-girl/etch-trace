"""Real database transactions cover competing commands and callback replay."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from conftest import API, Wire, detail, event, headers, task
from fastapi.testclient import TestClient
from main import create_app
from v1_commands import dispatch_failed
from v1_models import Settings


@pytest.mark.parametrize("name,role,expected", [
    ("other", "worker", 404), ("reader", "engineer", 404),
    ("reader", "admin", 404), ("owner", "worker", 202),
])
def test_only_owner_can_answer_waiting_question(
    client: TestClient, name: str, role: str, expected: int,
) -> None:
    # Given a task waiting for its owner's input.
    tid = task(client)
    assert event(client, tid, "QUESTION", {"text": "Which chamber?"}).status_code == 200
    # When an actor responds.
    response = client.post(f"{API}/{tid}/messages", headers=headers(name, role),
                           json={"text": "CH-A"})
    # Then only the owner resumes and their identity is persisted.
    assert response.status_code == expected
    data = detail(client, tid)
    assert data.status == ("RUNNING" if expected == 202 else "WAITING_INPUT")
    if expected == 202:
        assert data.messages[-1].user_name == name
        assert data.messages[-1].text == "CH-A"


@pytest.mark.parametrize("role,expected", [("worker", 403), ("admin", 403), ("engineer", 202)])
def test_only_engineer_reviews(client: TestClient, role: str, expected: int) -> None:
    # Given a reviewable report.
    tid = task(client)
    event(client, tid, "APPROVAL_REQUIRED", {"report": {"summary": "Hypothesis"}})
    # When an actor approves.
    response = client.post(f"{API}/{tid}/approval", headers=headers("reviewer", role),
                           json={"action": "approve", "comment": "Reviewed"})
    # Then only an engineer can transition the task.
    assert response.status_code == expected
    if expected == 202:
        assert detail(client, tid).reviews[0].user_name == "reviewer"


def test_approval_preserves_reviewed_snapshot_with_identity(client: TestClient) -> None:
    # Given an approved report and server-derived reviewer identity.
    tid = task(client)
    event(client, tid, "APPROVAL_REQUIRED", {"report": {"summary": "Reviewed hypothesis"}})
    client.post(f"{API}/{tid}/approval", headers=headers("엔지니어", "engineer"), json={
        "action": "approve", "comment": "Verified evidence", "lot_id": "LOT-1",
        "event_time": "2026-10-20T01:00:00Z",
    })
    # When the agent completes with its final report.
    rejected = event(client, tid, "DONE", {"report": {"summary": "Final hypothesis"}})
    assert rejected.status_code == 409
    response = event(client, tid, "DONE", {"report": {"summary": "Reviewed hypothesis"}})
    # Then approval is audited against the exact report the engineer reviewed.
    assert response.status_code == 200
    data = detail(client, tid)
    assert data.status == "DONE"
    assert data.report is not None
    assert data.report.summary == "Reviewed hypothesis"
    assert data.investigation is not None
    assert data.investigation.report.summary == "Reviewed hypothesis"
    assert data.investigation.approved_by == "엔지니어"
    assert data.investigation.lot_id == "LOT-1"


def test_callback_idempotency_is_scoped_to_command(client: TestClient) -> None:
    # Given an acknowledged callback in a suspended command.
    tid = task(client)
    command = str(detail(client, tid).command_id)
    first = event(client, tid, "QUESTION", {"text": "Chamber?"}, "one", command)
    assert first.status_code == 200
    # When that exact callback is retried.
    response = event(client, tid, "QUESTION", {"text": "Chamber?"}, "one", command)
    # Then no duplicate event or message is persisted.
    assert response.json() == {"accepted": False, "duplicate": True}
    data = detail(client, tid)
    assert len([e for e in data.events if e.type == "QUESTION"]) == 1
    assert len(data.messages) == 2


def test_stale_completion_cannot_finish_new_command(client: TestClient) -> None:
    # Given a new owner response after an earlier question.
    tid = task(client)
    old = str(detail(client, tid).command_id)
    event(client, tid, "QUESTION", {"text": "Chamber?"})
    client.post(f"{API}/{tid}/messages", headers=headers(), json={"text": "CH-A"})
    # When a delayed completion arrives for the earlier command.
    response = event(client, tid, "DONE", {"report": {}}, "late", old)
    # Then the active command is untouched.
    assert response.status_code == 409
    assert detail(client, tid).status == "RUNNING"


def test_competing_reviews_only_dispatch_one_resume(client: TestClient, wire: Wire) -> None:
    # Given one waiting approval and two synchronized reviewers.
    tid = task(client)
    wire.commands.get_nowait()
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    barrier = Barrier(2)

    def review(name: str) -> int:
        barrier.wait(timeout=5)
        return client.post(f"{API}/{tid}/approval", headers=headers(name, "engineer"),
                           json={"action": "revise", "comment": name}).status_code
    # When both reviewers submit concurrently.
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(review, ["A", "B"]))
    # Then exactly one claims the waiting state and dispatches.
    assert sorted(responses) == [202, 409]
    assert wire.commands.qsize() == 1
    assert len(detail(client, tid).reviews) == 1


def test_dispatch_failure_becomes_visible(client: TestClient, wire: Wire) -> None:
    # Given an agent rejecting HTTP commands.
    wire.status = 503
    # When a task is submitted.
    tid = task(client)
    # Then its failed state and error survive in event history.
    data = detail(client, tid)
    assert data.status == "FAILED"
    assert data.events[-1].type == "FAILED"
    assert "503" in str(data.events[-1].payload["error"])


def test_old_dispatch_failure_cannot_fail_resumed_command(client: TestClient) -> None:
    # Given a command resumed after a question.
    tid = task(client)
    old = detail(client, tid).command_id
    event(client, tid, "QUESTION", {"text": "Chamber?"})
    client.post(f"{API}/{tid}/messages", headers=headers(), json={"text": "CH-A"})
    # When a delayed dispatch failure from the old command arrives.
    dispatch_failed(client.app.state.store, UUID(tid), old, "Old timeout")
    # Then it cannot fail the new command.
    assert detail(client, tid).status == "RUNNING"


@pytest.mark.parametrize("status", ["WAITING_INPUT", "WAITING_APPROVAL", "RUNNING", "QUEUED"])
def test_restart_only_fails_interrupted_active_tasks(
    client: TestClient, database_url: str, wire: Wire, status: str,
) -> None:
    # Given a stored task in one startup-relevant state.
    tid = task(client)
    with client.app.state.store.pool.connection() as conn:
        conn.execute("UPDATE v1_tasks SET status=%s WHERE id=%s", (status, tid))
    # When another backend lifespan recovers the database.
    with TestClient(create_app(Settings(database_url, wire.url, "test-key"))) as restarted:
        data = detail(restarted, tid)
    # Then waiting checkpoints are preserved and active work visibly fails.
    assert data.status == (status if status.startswith("WAITING") else "FAILED")


@pytest.mark.parametrize("kind", ["DONE", "INCOMPLETE", "FAILED"])
def test_terminal_callbacks_reject_later_events(client: TestClient, kind: str) -> None:
    # Given a terminal task.
    tid = task(client)
    if kind == "DONE":
        event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
        client.post(f"{API}/{tid}/approval", headers=headers("reviewer", "engineer"),
                    json={"action": "approve"})
    event(client, tid, kind, {"report": {}} if kind == "DONE" else {})
    # When a new progress callback arrives.
    response = event(client, tid, "SEARCH_STARTED")
    # Then it cannot reopen the task.
    assert response.status_code == 409
    assert detail(client, tid).status == kind


def test_investigation_api_requires_approval_and_deduplicates(client: TestClient) -> None:
    tid = task(client)
    url = f"/internal/tasks/{tid}/investigation"
    body = {"type": "DONE", "event_id": "save-1", "payload": {"report": {}}}
    auth = {"X-Internal-Key": "test-key", "X-Command-ID": str(detail(client, tid).command_id)}
    assert client.post(url, headers=auth, json=body).status_code == 409
    assert detail(client, tid).investigation is None
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    client.post(f"{API}/{tid}/approval", headers=headers("reviewer", "engineer"),
                json={"action": "approve", "lot_id": "LOT-1"})
    auth["X-Command-ID"] = str(detail(client, tid).command_id)
    assert client.post(url, json=body).status_code == 401
    assert client.post(url, headers=auth, json=body).json() == {
        "accepted": True, "duplicate": False,
    }
    assert client.post(url, headers=auth, json=body).json() == {
        "accepted": False, "duplicate": True,
    }
    data = detail(client, tid)
    assert data.investigation.approved_by == "reviewer"
    assert data.investigation.lot_id == "LOT-1"
    assert len([e for e in data.events if e.type == "DONE"]) == 1


def test_internal_history_excludes_unsaved_and_filters_owner(client: TestClient) -> None:
    tid = task(client)
    task(client, name="another")
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    client.post(f"{API}/{tid}/approval", headers=headers("reviewer", "engineer"),
                json={"action": "approve"})
    event(client, tid, "DONE", {"report": {}})
    url = "/internal/investigations"
    key = {"X-Internal-Key": "test-key"}
    query = {"user_name": "owner", "user_role": "worker"}
    assert client.get(url, params=query).status_code == 401
    rows = client.get(url, headers=key, params=query).json()
    assert [row["id"] for row in rows] == [tid]
    query["user_name"] = "another"
    assert client.get(url, headers=key, params=query).json() == []
    assert client.get(f"{url}/{tid}", headers=key, params=query).status_code == 404
    query["user_role"] = "engineer"
    result = client.get(f"{url}/{tid}", headers=key, params=query).json()
    assert result["report"]["demo"] is True
    assert result["approved_by"] == "reviewer"
    assert not ({"messages", "events", "reviews", "command_id"} & result.keys())
