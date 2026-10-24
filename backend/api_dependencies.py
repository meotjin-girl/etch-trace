"""Lifespan-owned runtime access and shared authentication dependencies."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request
from investigations_store import InvestigationsStore
from v1_auth import Authenticator, internal
from v1_models import Actor, Settings
from v1_store import Store


@dataclass(frozen=True, slots=True)
class Runtime:
    store: Store
    settings: Settings
    authenticator: Authenticator
    investigations: InvestigationsStore


@dataclass(frozen=True, slots=True)
class Dependencies:
    current: Callable[[], Runtime]

    def actor(self, request: Request) -> Actor:
        return self.current().authenticator.authenticate(request.headers.get("authorization"))

    def internal(self, request: Request) -> None:
        internal(
            self.current().settings.internal_api_key,
            request.headers.get("x-internal-key") or request.headers.get("x-internal-api-key"),
        )
