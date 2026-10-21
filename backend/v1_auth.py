"""Validate Keycloak access tokens; internal services use separate credentials."""

from secrets import compare_digest
from typing import ClassVar, Literal

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from v1_models import Actor, Settings


class Claims(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    sub: str = Field(min_length=1)
    exp: int
    typ: Literal["Bearer"]
    preferred_username: str = ""
    name: str = ""


class Authenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings
        self.keys: PyJWKClient = PyJWKClient(
            settings.keycloak_jwks_url or f"{settings.issuer}/protocol/openid-connect/certs",
            timeout=5,
            lifespan=300,
        )

    def authenticate(self, authorization: str | None) -> Actor:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token or " " in token:
            raise HTTPException(
                401,
                "Bearer access token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            key = self.keys.get_signing_key_from_jwt(token)
            data = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.settings.issuer,
                audience=self.settings.keycloak_audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            claims = Claims.model_validate(data)
            if not claims.sub.strip():
                raise HTTPException(401, "Invalid access token")
        except PyJWKClientConnectionError as exc:
            raise HTTPException(503, "Login service is unavailable") from exc
        except (jwt.InvalidTokenError, PyJWKClientError, ValidationError, TypeError) as exc:
            raise HTTPException(
                401,
                "Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        name = claims.preferred_username.strip() or claims.name.strip() or claims.sub
        return Actor(name, "user", claims.sub, claims.exp)


def internal(expected: str, key: str | None) -> None:
    if not key or not compare_digest(key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid internal API key")
