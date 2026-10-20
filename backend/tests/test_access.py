"""Exercise identity and resource scopes through the HTTP API."""

from uuid import uuid4

import psycopg
import pytest
from conftest import API, KEY, detail, event, headers, task
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb


@pytest.mark.parametrize("identity", [{}, headers(role="bad"), headers(name=" ")])
def test_authentication_is_required(client: TestClient, identity: dict[str, str]) -> None:
    # Given an unauthenticated or invalid identity.
    # When listing tasks.
    response = client.get(API, headers=identity)
    # Then no data is disclosed.
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["worker", "engineer", "admin"])
def test_list_scope_depends_on_role(client: TestClient, role: str) -> None:
    # Given tasks from two distinct owners.
    own = task(client)
    other = task(client, "other")
    # When listing as each supported role.
    response = client.get(API, headers=headers(role=role))
    # Then workers only see their own complete summaries.
    rows = response.json()
    assert {row["id"] for row in rows} == ({own} if role == "worker" else {own, other})
    assert {"user_name", "user_role", "question", "status", "report", "created_at",
            "updated_at"} <= rows[0].keys()


@pytest.mark.parametrize("suffix", ["", "/events", "/stream?user_name=other&user_role=worker"])
def test_workers_cannot_read_others_tasks(client: TestClient, suffix: str) -> None:
    # Given another user's task.
    tid = task(client)
    # When reading any task surface.
    response = client.get(f"{API}/{tid}{suffix}", headers=headers("other"))
    # Then the resource remains undisclosed.
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["engineer", "admin"])
def test_broad_roles_can_read_detail(client: TestClient, role: str) -> None:
    # Given an existing task.
    tid = task(client, "홍길동")
    # When a broad reader requests detail.
    response = client.get(f"{API}/{tid}", headers=headers("reader", role))
    # Then the stored identity and full history are returned.
    data = response.json()
    assert response.status_code == 200
    assert data["user_name"] == "홍길동"
    assert data["messages"][0]["user_name"] == "홍길동"
    assert {"messages", "events", "reviews", "investigation"} <= data.keys()


@pytest.mark.parametrize("path", ["/internal/cases", f"/internal/tasks/{uuid4()}/events"])
def test_internal_routes_require_secret(client: TestClient, path: str) -> None:
    # Given a caller without internal credentials.
    # When requesting an internal route.
    response = client.get(path) if path.endswith("cases") else client.post(path, json={})
    # Then service authentication rejects the request.
    assert response.status_code == 401


def test_cases_are_sorted_data_records(client: TestClient, database_url: str) -> None:
    # Given independently seeded business data.
    with psycopg.connect(database_url) as conn:
        conn.execute("CREATE TABLE etch_cases (id text PRIMARY KEY,data jsonb)")
        conn.execute("INSERT INTO etch_cases VALUES (%s,%s),(%s,%s)",
                     ("B", Jsonb({"id": "B"}), "A", Jsonb({"id": "A"})))
    # When the agent requests cases.
    response = client.get("/internal/cases", headers=KEY)
    # Then it receives data, not storage wrappers.
    assert response.json() == [{"id": "A"}, {"id": "B"}]


def test_sse_replays_after_larger_cursor_and_closes_terminal(client: TestClient) -> None:
    # Given a terminal task with persisted events.
    tid = task(client)
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    client.post(f"{API}/{tid}/approval", headers=headers("reviewer", "engineer"),
                json={"action": "approve"})
    assert event(client, tid, "DONE", {"report": {}}).status_code == 200
    rows = detail(client, tid).events
    cursor = rows[-2].seq
    # When reconnecting with both cursor mechanisms.
    response = client.get(
        f"{API}/{tid}/stream?user_name=owner&user_role=worker&after=0",
        headers={"Last-Event-ID": str(cursor)},
    )
    # Then only events after the greater cursor replay.
    assert response.status_code == 200
    assert "event: DONE" in response.text
    assert "event: QUEUED" not in response.text
    assert f"id: {rows[-1].seq}" in response.text


def test_invalid_sse_cursor_is_rejected(client: TestClient) -> None:
    # Given an existing task.
    tid = task(client)
    # When an invalid replay cursor is supplied.
    response = client.get(
        f"{API}/{tid}/stream?user_name=owner&user_role=worker",
        headers={"Last-Event-ID": "NaN"},
    )
    # Then the API rejects malformed input before streaming.
    assert response.status_code == 422
