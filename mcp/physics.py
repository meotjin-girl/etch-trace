"""Physics MCP exposing deterministic, versioned etch calculations."""

import os

from fastmcp import FastMCP
from physics_models import PhysicsInputs, PhysicsResult
from physics_models import evaluate_etch_physics as evaluate

mcp = FastMCP("etch-physics", version="1.0.0")


@mcp.tool
def evaluate_etch_physics(inputs: PhysicsInputs) -> list[PhysicsResult]:
    """Calculate supported zero-order etch relations without inventing inputs."""
    return evaluate(inputs)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
