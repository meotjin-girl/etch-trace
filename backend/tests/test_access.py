"""Exercise identity and resource scopes through the HTTP API."""

from datetime import UTC, datetime
from uuid import uuid4

import jwt
import main
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
def test_authenticated_users_share_all_tasks(client: TestClient, role: str) -> None:
    # Given tasks from two distinct owners.
    own = task(client)
    other = task(client, "other")
    # When listing as each supported role.
    response = client.get(API, headers=headers(role=role))
    # Then realm role labels do not restrict shared task visibility.
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
def test_authenticated_users_can_read_others_tasks(client: TestClient, suffix: str) -> None:
    # Given another user's task.
    tid = task(client)
    event(client, tid, "FAILED", {"error": "Test complete"})
    # When reading any task surface.
    response = client.get(f"{API}/{tid}{suffix}", headers=headers("other"))
    # Then shared work is readable on every surface.
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
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    client.post(
        f"{API}/{tid}/approval", headers=headers("reviewer", "engineer"), json={"action": "approve"}
    )
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


def test_public_history_is_served_by_backend_with_shared_access(client: TestClient) -> None:
    tid = task(client)
    task(client, name="another")
    event(client, tid, "APPROVAL_REQUIRED", {"report": {}})
    client.post(
        f"{API}/{tid}/approval",
        headers=headers("reviewer", "engineer"),
        json={"action": "approve", "lot_id": "LOT-1"},
    )
    event(client, tid, "DONE", {"report": {}})
    url = "/api/ai/investigations"
    assert client.get(url).status_code == 401
    assert [row["id"] for row in client.get(url, headers=headers()).json()] == [tid]
    assert [row["id"] for row in client.get(url, headers=headers("another")).json()] == [tid]
    assert client.get(f"{url}/{tid}", headers=headers("another")).status_code == 200
    result = client.get(f"{url}/{tid}", headers=headers("reader", "engineer")).json()
    assert result["approved_by"] == "reviewer"
    assert result["approved_by_id"] == "account:reviewer"
    assert result["lot_id"] == "LOT-1"
    assert not ({"messages", "events", "reviews", "command_id"} & result.keys())
    assert client.get(f"{url}/not-a-uuid", headers=headers()).status_code == 422
    unsaved = task(client)
    assert client.get(f"{url}/{unsaved}", headers=headers()).status_code == 404


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iss": "https://other.example/realms/trace"},
        {"aud": "other-api"},
        {"sub": ""},
        {"sub": " "},
        {"typ": "ID"},
        {"exp": None},
        {"sub": None},
    ],
)
def test_invalid_access_tokens_are_rejected(
    client: TestClient,
    claims: dict[str, str | int | None],
) -> None:
    # Given signed claims that do not identify a valid access session.
    bearer = token(**claims)
    # When requesting protected data.
    response = client.get(API, headers={"Authorization": f"Bearer {bearer}"})
    # Then signature alone does not authenticate.
    assert response.status_code == 401


@pytest.mark.parametrize("failure", ["signature", "missing_exp", "algorithm", "unknown_key"])
def test_untrusted_jwt_cannot_authenticate(client: TestClient, failure: str) -> None:
    # Given an untrusted signature, algorithm, key or missing expiry.
    claims = jwt.decode(token(), options={"verify_signature": False})
    match failure:
        case "signature":
            encoded = token()
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
    # When accessing the API.
    response = client.get(API, headers={"Authorization": f"Bearer {encoded}"})
    # Then no data is disclosed.
    assert response.status_code == 401


def test_jwks_outage_is_distinct_from_invalid_identity(client: TestClient, wire: Wire) -> None:
    # Given no cached key and a failing JWKS service.
    wire.jwks_status = 503
    # When authenticating a signed access token.
    response = client.get(API, headers=headers())
    # Then the API reports the upstream outage.
    assert response.status_code == 503


@pytest.mark.parametrize(
    "path",
    [
        API,
        f"{API}/{uuid4()}",
        f"{API}/{uuid4()}/events",
        f"{API}/{uuid4()}/stream",
        "/api/ai/investigations",
        f"/api/ai/investigations/{uuid4()}",
        "/api/sops",
        "/api/sops/SOP-ETCH-12",
    ],
)
def test_all_public_read_surfaces_require_bearer(client: TestClient, path: str) -> None:
    # Given spoofed mock identity headers and URL credentials.
    # When reading each public data surface without an Authorization header.
    response = client.get(
        path,
        params={"user_name": "owner", "user_role": "engineer", "access_token": token()},
        headers={"X-User-Name": "owner", "X-User-Role": "engineer"},
    )
    # Then neither legacy identity nor a URL token is accepted.
    assert response.status_code == 401


def test_actor_is_derived_from_signed_claims(client: TestClient) -> None:
    # Given signed identity and spoofed display headers.
    # When creating work.
    response = client.post(
        API,
        headers={**headers("actual"), "X-User-Name": "spoof", "X-User-Role": "admin"},
        json={"question": "Investigate"},
    )
    # Then stable account identity is server-derived.
    data = detail(client, response.json()["taskId"])
    assert data.user_id == "account:actual"
    assert data.user_name == "actual"
    assert data.user_role == "user"
    assert data.messages[0].user_id == "account:actual"


def test_stream_stops_when_its_verified_token_expires(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given an authenticated stream whose token expires before event generation.
    tid = task(client)

    class ExpiredClock:
        @staticmethod
        def now(tz: None = None) -> datetime:
            return datetime(2101, 1, 1, tzinfo=UTC)

    monkeypatch.setattr(main, "datetime", ExpiredClock)
    # When the stream starts without advancing wall time or sleeping.
    response = client.get(f"{API}/{tid}/stream", headers=headers())
    # Then no persisted events are sent after expiry.
    assert response.status_code == 200
    assert response.text == ""
    assert detail(client, tid).status == "RUNNING"


def test_auth_config_contains_only_public_adapter_settings(client: TestClient) -> None:
    # Given an anonymous browser bootstrapping login.
    # When fetching adapter configuration.
    response = client.get("/api/auth/config")
    # Then only public connection settings are returned.
    assert response.json() == {
        "url": "http://localhost:8080/auth",
        "realm": "trace",
        "clientId": "trace-web",
    }
