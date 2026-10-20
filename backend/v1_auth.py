"""Development identity and internal service authentication boundaries."""

from secrets import compare_digest
from urllib.parse import unquote

from fastapi import HTTPException, Request
from v1_models import Actor, Role


def identity(name: str | None, role: str | None) -> Actor:
    if not name or role not in {"worker", "engineer", "admin"}:
        raise HTTPException(401, "X-User-Name and a valid X-User-Role are required")
    decoded = unquote(name).strip()
    if not decoded:
        raise HTTPException(401, "User name must not be blank")
    parsed_role: Role
    match role:
        case "worker":
            parsed_role = "worker"
        case "engineer":
            parsed_role = "engineer"
        case "admin":
            parsed_role = "admin"
        case _:
            raise HTTPException(401, "Invalid role")
    return Actor(decoded, parsed_role)


def actor(request: Request) -> Actor:
    return identity(request.headers.get("x-user-name"), request.headers.get("x-user-role"))


def internal(expected: str, key: str | None) -> None:
    if not key or not compare_digest(key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid internal API key")
