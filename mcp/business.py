"""Business MCP: read cases only through the authenticated backend endpoint."""

from __future__ import annotations

import os
from contextlib import closing
from http.client import HTTPConnection, HTTPSConnection
from urllib.error import HTTPError
from urllib.parse import urlsplit

from fastmcp import FastMCP
from pydantic import TypeAdapter

from evidence import Case, Context, MetricAnalysis, ScoredCase
from evidence import analyze_metrics as calculate_metrics
from evidence import search_cases as score_cases


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


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
