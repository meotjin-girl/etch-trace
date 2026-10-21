"""Exercise identity and resource scopes through the HTTP API."""

from uuid import uuid4

import jwt
import psycopg
import pytest
from conftest import API, KEY, SIGNING_KEY, Wire, detail, event, headers, task, token
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb


@pytest.mark.parametrize(
    "identity",
    [
        {},
        {"X-User-Name": "owner", "X-User-Role": "engineer"},
        {"Authorization": "Bearer invalid"},
        {"Authorization": "Basic invalid"},
    ],
)
def test_authentication_is_required(client: TestClient, identity: dict[str, str]) -> None:
    # Given an unauthenticated or invalid identity.
    # When listing tasks.
    response = client.get(API, headers=identity)
    # Then no data is disclosed.
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["worker", "engineer", "admin"])
def test_logged_in_users_share_all_tasks(client: TestClient, role: str) -> None:
    # Given tasks from two distinct owners.
    own = task(client)
    other = task(client, "other")
    # When listing as each supported role.
    response = client.get(API, headers=headers(role=role))
    # Then every authenticated user sees all complete summaries.
    rows = response.json()
    assert {row["id"] for row in rows} == {own, other}
    assert {
        "user_name",
        "user_role",
        "question",
        "status",
        "report",
        "created_at",
        "updated_at",
    } <= rows[0].keys()


@pytest.mark.parametrize("suffix", ["", "/events", "/stream"])
def test_users_can_read_others_tasks(client: TestClient, suffix: str) -> None:
    # Given another user's task.
    tid = task(client)
    event(client, tid, "DONE", {"report": {}})
    # When reading any task surface.
    response = client.get(f"{API}/{tid}{suffix}", headers=headers("other"))
    # Then shared work is accessible on every surface.
    assert response.status_code == 200


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
        conn.execute(
            "INSERT INTO etch_cases VALUES (%s,%s),(%s,%s)",
            ("B", Jsonb({"id": "B"}), "A", Jsonb({"id": "A"})),
        )
    # When the agent requests cases.
    response = client.get("/internal/cases", headers=KEY)
    # Then it receives data, not storage wrappers.
    assert response.json() == [{"id": "A"}, {"id": "B"}]


def test_sse_replays_after_larger_cursor_and_closes_terminal(client: TestClient) -> None:
    # Given a terminal task with persisted events.
    tid = task(client)
    assert event(client, tid, "DONE", {"report": {}}).status_code == 200
    rows = detail(client, tid).events
    cursor = rows[-2].seq
    # When reconnecting with both cursor mechanisms.
    response = client.get(
        f"{API}/{tid}/stream?user_name=owner&user_role=worker&after=0",
        headers={**headers(), "Last-Event-ID": str(cursor)},
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
        headers={**headers(), "Last-Event-ID": "NaN"},
    )
    # Then the API rejects malformed input before streaming.
    assert response.status_code == 422


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iss": "https://other.example/realms/trace"},
        {"aud": "other-api"},
        {"sub": ""},
        {"typ": "ID"},
        {"exp": None},
        {"sub": None},
    ],
)
def test_invalid_access_tokens_are_rejected(
    client: TestClient, claims: dict[str, str | int | None]
) -> None:
    # Given a signed token with an invalid required claim.
    bearer = token(**claims)
    # When accessing the API.
    response = client.get(API, headers={"Authorization": f"Bearer {bearer}"})
    # Then signature alone is insufficient.
    assert response.status_code == 401


def test_sse_rejects_query_and_mock_identity_without_bearer(client: TestClient) -> None:
    # Given an existing task and the old identity transport.
    tid = task(client)
    # When connecting without a bearer token.
    response = client.get(
        f"{API}/{tid}/stream?user_name=owner&user_role=engineer&access_token={token()}",
        headers={"X-User-Name": "owner", "X-User-Role": "engineer"},
    )
    # Then neither mock identity nor URL tokens authenticate the stream.
    assert response.status_code == 401


def test_actor_is_derived_from_signed_claims(client: TestClient) -> None:
    # Given an access token and spoofed display headers.
    # When creating shared work.
    response = client.post(
        API,
        headers={
            **headers("actual"),
            "X-User-Name": "spoof",
            "X-User-Role": "admin",
        },
        json={"question": "Investigate"},
    )
    # Then stable identity and display name come only from Keycloak claims.
    data = detail(client, response.json()["taskId"])
    assert data.user_id == "account:actual"
    assert data.user_name == "actual"
    assert data.messages[0].user_id == "account:actual"


@pytest.mark.parametrize("failure", ["signature", "missing_exp", "algorithm", "unknown_key"])
def test_untrusted_jwt_cannot_authenticate(client: TestClient, failure: str) -> None:
    # Given a token whose signature, key, algorithm or required claims are invalid.
    claims = jwt.decode(token(), options={"verify_signature": False})
    match failure:
        case "signature":
            encoded = jwt.encode(
                claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"}
            )
            parts = encoded.split(".")
            parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
            encoded = ".".join(parts)
        case "missing_exp":
            del claims["exp"]
            encoded = jwt.encode(
                claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"}
            )
        case "algorithm":
            encoded = jwt.encode(
                claims,
                "not-a-keycloak-signing-key-for-test",
                algorithm="HS256",
                headers={"kid": "test-key"},
            )
        case "unknown_key":
            encoded = jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "unknown"})
        case _:
            raise AssertionError(failure)
    # When requesting shared work.
    response = client.get(API, headers={"Authorization": f"Bearer {encoded}"})
    # Then no unsigned or misconfigured identity is accepted.
    assert response.status_code == 401


def test_jwks_outage_is_distinct_from_invalid_identity(client: TestClient, wire: Wire) -> None:
    # Given an unreachable key service with no cached key.
    wire.jwks_status = 503
    # When authenticating a valid token.
    response = client.get(API, headers=headers())
    # Then callers can distinguish a service outage from an expired session.
    assert response.status_code == 503
