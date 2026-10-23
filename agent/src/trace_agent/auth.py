# Copyright 2026 TRACE contributors
"""Keycloak access-token authentication and the isolated internal emitter path."""

from functools import lru_cache
from hmac import compare_digest
from typing import ClassVar, Literal, TypedDict

import anyio
import jwt
from jwt import PyJWKClient
from langgraph_sdk import Auth
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from .config import Settings
from .errors import ConfigurationError

auth = Auth()


class Claims(BaseModel):
    """Keycloak access-token claims after cryptographic validation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    sub: str = Field(min_length=1)
    typ: Literal["Bearer"]
    exp: int


class User(TypedDict):
    """Authenticated identity; no owner metadata or resource filters."""

    identity: str
    permissions: list[str]


@lru_cache(maxsize=4)
def jwks_client(url: str) -> PyJWKClient:
    """Cache the issuer's key set; PyJWT refreshes it when an unknown kid arrives."""
    return PyJWKClient(url, timeout=10, lifespan=300)


def verify_token(token: str, settings: Settings) -> User:
    """Validate RS256, issuer, audience, expiration, subject, and access-token type."""
    if not settings.issuer:
        raise ConfigurationError(variable="KEYCLOAK_ISSUER")
    url = settings.keycloak_jwks_url or (
        settings.issuer.rstrip("/") + "/protocol/openid-connect/certs"
    )
    signing_key = jwks_client(url).get_signing_key_from_jwt(token)
    claims = Claims.model_validate(
        jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.issuer,
            audience=settings.keycloak_audience,
            options={"require": ["exp", "sub", "typ", "iss", "aud"]},
        )
    )
    return {"identity": claims.sub, "permissions": ["read", "write"]}


@auth.authenticate
async def authenticate(headers: dict[bytes, bytes], authorization: str | None = None) -> User:
    """Use explicit local Studio credentials, otherwise validate the bearer first."""
    settings = Settings()
    expected = settings.internal_api_key.get_secret_value().encode()
    provided = headers.get(b"x-internal-key", b"")
    internal_authenticated = bool(expected and provided and compare_digest(expected, provided))
    # Studio keeps its LangSmith bearer even with custom connection headers.
    # nginx strips both of these headers; only a trusted local caller can use it.
    schemes = {value.strip().lower() for value in headers.get(b"x-auth-scheme", b"").split(b",")}
    if b"custom" in schemes and internal_authenticated:
        return {"identity": "trace-local-studio", "permissions": ["read", "write"]}
    supplied = authorization
    if supplied is None and b"authorization" in headers:
        supplied = headers[b"authorization"].decode("latin-1")
    if supplied is not None:
        scheme, separator, token = supplied.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid bearer token")
        try:
            return await anyio.to_thread.run_sync(verify_token, token, settings)
        except (jwt.PyJWTError, ValidationError) as error:
            raise Auth.exceptions.HTTPException(
                status_code=401, detail="Invalid bearer token"
            ) from error
    if internal_authenticated:
        return {"identity": "trace-alert-emitter", "permissions": ["read", "write"]}
    raise Auth.exceptions.HTTPException(status_code=401, detail="Authentication required")


@auth.on
async def authorize(*, ctx: Auth.types.AuthContext, value: dict[str, JsonValue]) -> bool:
    """All authenticated users share threads; no ownership filters are installed."""
    del value
    return ctx.user.is_authenticated
