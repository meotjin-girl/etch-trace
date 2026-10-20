"""Business MCP: case evidence and approved history through authenticated backend APIs."""

from __future__ import annotations

import json
import os
from contextlib import closing
from http.client import HTTPConnection, HTTPSConnection
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from evidence import Case, Context, MetricAnalysis, ScoredCase
from evidence import analyze_metrics as calculate_metrics
from evidence import search_cases as score_cases
from fastmcp import FastMCP
from pydantic import JsonValue, TypeAdapter

mcp = FastMCP("etch-business", version="1.0.0")


@mcp.tool
def search_cases(context: Context) -> list[ScoredCase]:
    """Find up to five demo cases using structured frontend search context."""
    url = f"{os.environ['BACKEND_URL'].rstrip('/')}/internal/cases"
    target = urlsplit(url)
    connection_type = HTTPSConnection if target.scheme == "https" else HTTPConnection
    with closing(connection_type(target.netloc, timeout=30)) as connection:
        connection.request(
            "GET",
            target.path,
            headers={
                "X-Internal-Key": os.environ["INTERNAL_API_KEY"],
                "Accept": "application/json",
            },
        )
        with connection.getresponse() as response:
            if response.status != 200:
                raise HTTPError(url, response.status, response.reason, response.headers, response)
            cases = TypeAdapter(list[Case]).validate_json(response.read())
    return score_cases(cases, context)


@mcp.tool
def analyze_metrics(
    cases: list[Case], metrics: dict[str, float]
) -> list[MetricAnalysis]:
    """Compare supplied case observations and return linked population statistics."""
    return calculate_metrics(cases, metrics)


@mcp.tool
def save_investigation(
    task_id: UUID, command_id: UUID, event_id: str, payload: dict[str, JsonValue],
) -> dict[str, bool]:
    """Save an approved investigation through backend validation, never direct SQL.

    Reuse event_id and command_id on retries. The backend owns the reviewed
    snapshot, reviewer identity, approval checks and duplicate suppression.
    """
    url = f"{os.environ['BACKEND_URL'].rstrip('/')}/internal/tasks/{task_id}/investigation"
    target = urlsplit(url)
    connection_type = HTTPSConnection if target.scheme == "https" else HTTPConnection
    body = json.dumps({"type": "DONE", "event_id": event_id, "payload": payload})
    with closing(connection_type(target.netloc, timeout=30)) as connection:
        connection.request("POST", target.path, body=body.encode(), headers={
            "X-Internal-Key": os.environ["INTERNAL_API_KEY"],
            "X-Command-ID": str(command_id),
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        with connection.getresponse() as response:
            if response.status != 200:
                raise HTTPError(url, response.status, response.reason, response.headers, response)
            return TypeAdapter(dict[str, bool]).validate_json(response.read())


def _read_investigations(user_name: str, user_role: str, task_id: UUID | None = None):
    path = "/internal/investigations" + (f"/{task_id}" if task_id else "")
    url = f"{os.environ['BACKEND_URL'].rstrip('/')}{path}"
    target = urlsplit(url)
    connection_type = HTTPSConnection if target.scheme == "https" else HTTPConnection
    query = urlencode({"user_name": user_name, "user_role": user_role})
    with closing(connection_type(target.netloc, timeout=30)) as connection:
        connection.request("GET", f"{target.path}?{query}", headers={
            "X-Internal-Key": os.environ["INTERNAL_API_KEY"], "Accept": "application/json",
        })
        with connection.getresponse() as response:
            if response.status != 200:
                raise HTTPError(url, response.status, response.reason, response.headers, response)
            return json.loads(response.read())


@mcp.tool
def list_investigations(user_name: str, user_role: str) -> list[dict[str, JsonValue]]:
    """List saved approved investigations visible to the requesting identity."""
    return _read_investigations(user_name, user_role)


@mcp.tool
def get_investigation(task_id: UUID, user_name: str, user_role: str) -> dict[str, JsonValue]:
    """Read the approved investigation report and its storage metadata."""
    return _read_investigations(user_name, user_role, task_id)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
