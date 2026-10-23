# Copyright 2026 TRACE contributors
"""Signed tokens exercise the real PyJWT/JWKS validation path."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Final

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from langgraph_sdk import Auth
from pydantic import JsonValue, TypeAdapter

from trace_agent.auth import authenticate
from trace_agent.config import Settings

ISSUER: Final = "https://keycloak.example/auth/realms/trace"


@dataclass(frozen=True, slots=True)
class Tokens:
    key: rsa.RSAPrivateKey

    def sign(self, override: dict[str, JsonValue] | None = None) -> str:
        claims: dict[str, JsonValue] = {
            "iss": ISSUER,
            "aud": "trace-api",
            "sub": "collaborator-2",
            "typ": "Bearer",
            "exp": 4102444800,
        }
        claims.update(override or {})
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test-key"})


@pytest.fixture
def tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Tokens]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = TypeAdapter(dict[str, JsonValue]).validate_json(RSAAlgorithm.to_jwk(key.public_key()))
    public["kid"] = "test-key"
    jwks = tmp_path / "jwks.json"
    _ = jwks.write_text(json.dumps({"keys": [public]}))
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", "trace-api")
    monkeypatch.setenv("INTERNAL_API_KEY", "owned-test-key")
    with ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path))
    ) as server:
        monkeypatch.setenv("KEYCLOAK_JWKS_URL", f"http://127.0.0.1:{server.server_port}/jwks.json")
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            yield Tokens(key)
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.anyio
async def test_signed_access_token_authenticates_any_collaborator(tokens: Tokens) -> None:
    # Given / When: a signed JWT resolves its real public key from JWKS.
    user = await authenticate({}, f"Bearer {tokens.sign()}")

    # Then: the token subject, not a requested owner, becomes the identity.
    assert user["identity"] == "collaborator-2"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "override",
    [
        {"iss": "https://wrong.example"},
        {"aud": "wrong"},
        {"exp": 1},
        {"typ": "ID"},
        {"sub": ""},
        {"sub": None},
        {"exp": None},
    ],
)
async def test_invalid_signed_claims_do_not_fall_back_to_internal_key(
    tokens: Tokens, override: dict[str, JsonValue]
) -> None:
    # Given: a real signed token with one invalid claim and a correct internal key.
    token = tokens.sign(override)

    # When / Then: Authorization wins and fails closed.
    with pytest.raises(Auth.exceptions.HTTPException) as error:
        _ = await authenticate({b"x-internal-key": b"owned-test-key"}, f"Bearer {token}")
    assert error.value.status_code == 401


@pytest.mark.anyio
async def test_invalid_signature_is_rejected(tokens: Tokens) -> None:
    # Given: the issuer's kid but a different signing key.
    other = Tokens(rsa.generate_private_key(public_exponent=65537, key_size=2048))
    assert other.key != tokens.key

    # When / Then: the actual RSA signature check fails.
    with pytest.raises(Auth.exceptions.HTTPException):
        _ = await authenticate({}, f"Bearer {other.sign()}")


@pytest.mark.anyio
@pytest.mark.parametrize("authorization", ["", "Basic abc", "Bearer", "Bearer invalid"])
async def test_bad_authorization_never_uses_internal_key(
    tokens: Tokens, authorization: str
) -> None:
    # Given: a valid internal key alongside an invalid Authorization header.
    del tokens

    # When / Then: no fallback is possible, even for an empty header.
    with pytest.raises(Auth.exceptions.HTTPException):
        _ = await authenticate(
            {b"x-internal-key": b"owned-test-key", b"authorization": authorization.encode()}
        )


@pytest.mark.anyio
async def test_internal_key_authenticates_only_without_authorization(tokens: Tokens) -> None:
    # Given / When: only the internal emitter credential is present.
    del tokens
    user = await authenticate({b"x-internal-key": b"owned-test-key"})

    # Then: it is attributed to the emitter, not a fabricated human.
    assert user["identity"] == "trace-alert-emitter"


@pytest.mark.anyio
@pytest.mark.parametrize("scheme", [b"custom", b"langsmith, custom"])
async def test_explicit_local_studio_key_is_independent_of_studio_bearer(
    tokens: Tokens, scheme: bytes
) -> None:
    # Given: Studio's unrelated bearer and explicit, trusted local credentials.
    del tokens
    user = await authenticate(
        {
            b"x-auth-scheme": scheme,
            b"x-internal-key": b"owned-test-key",
            b"authorization": b"Bearer studio-session-not-a-keycloak-token",
        }
    )
    # Then: the validated local credential owns the identity, not that bearer.
    assert user["identity"] == "trace-local-studio"


@pytest.mark.anyio
@pytest.mark.parametrize("headers", [{}, {b"x-internal-key": b"wrong"}])
async def test_missing_or_bad_internal_key_is_rejected(
    tokens: Tokens, headers: dict[bytes, bytes]
) -> None:
    # Given / When / Then: no valid bearer or internal credential.
    del tokens
    with pytest.raises(Auth.exceptions.HTTPException):
        _ = await authenticate(headers)


def test_existing_keycloak_url_and_realm_derive_exact_issuer() -> None:
    # Given / When: the established deployment environment shape.
    settings = Settings(
        keycloak_issuer="", keycloak_url="https://keycloak.example/auth/", keycloak_realm="trace"
    )

    # Then: the exact public issuer includes the realm once.
    assert settings.issuer == ISSUER
