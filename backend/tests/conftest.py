"""Isolated real PostgreSQL schemas and a real HTTP agent boundary."""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from threading import Thread
from uuid import uuid4

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from httpx import Response
from main import create_app
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import JsonValue
from v1_models import Detail, Settings

API = "/api/ai/tasks"
KEY = {"X-Internal-Key": "test-key"}
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ISSUER = "http://localhost:8080/auth/realms/trace"


def headers(name: str = "owner", role: str = "worker") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(name, realm_access={'roles': [role]})}"}


def token(name: str = "owner", /, **overrides: JsonValue) -> str:
    claims: dict[str, JsonValue] = {
        "iss": ISSUER,
        "aud": "trace-api",
        "sub": f"account:{name}",
        "preferred_username": name,
        "typ": "Bearer",
        "exp": 4102444800,
        "iat": 1700000000,
    }
    claims.update(overrides)
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})


def settings(database_url: str, wire: "Wire", **overrides: str) -> Settings:
    return Settings(
        database_url,
        wire.url,
        "test-key",
        keycloak_jwks_url=f"{wire.url}/certs",
        **overrides,
    )


@dataclass
class Wire:
    """Mutable HTTP fixture records commands and selects response status."""

    commands: Queue[tuple[str, dict[str, str], dict[str, JsonValue]]] = field(default_factory=Queue)
    status: int = 202
    url: str = ""
    jwks_status: int = 200


@pytest.fixture
def wire() -> Iterator[Wire]:
    state = Wire()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            key = jwt.algorithms.RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
            key["kid"] = "test-key"
            self.send_response(state.jwks_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"keys": [key]}).encode())

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.commands.put((self.path, dict(self.headers), body))
            self.send_response(state.status)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format: str, *args: str) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def database_url() -> Iterator[str]:
    base = os.getenv("TEST_DATABASE_URL", "postgresql:///postgres")
    schema = f"backend_test_{uuid4().hex}"
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield make_conninfo(base, options=f"-csearch_path={schema}")
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def client(database_url: str, wire: Wire) -> Iterator[TestClient]:
    app = create_app(settings(database_url, wire))
    with TestClient(app) as test_client:
        yield test_client


def task(client: TestClient, name: str = "owner", role: str = "worker") -> str:
    response = client.post(API, headers=headers(name, role), json={"question": "Investigate etch"})
    assert response.status_code == 202, response.text
    return response.json()["taskId"]


def detail(client: TestClient, tid: str) -> Detail:
    response = client.get(f"{API}/{tid}", headers=headers("reader", "engineer"))
    return Detail.model_validate(response.json())


def event(
    client: TestClient,
    tid: str,
    kind: str,
    payload: dict[str, JsonValue] | None = None,
    event_id: str | None = None,
    command_id: str | None = None,
) -> Response:
    command = command_id or str(detail(client, tid).command_id)
    return client.post(
        f"/internal/tasks/{tid}/events",
        headers={**KEY, "X-Command-ID": command},
        json={"event_id": event_id or uuid4().hex, "type": kind, "payload": payload or {}},
    )
