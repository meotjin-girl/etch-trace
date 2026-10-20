"""MCP gateway for the history panel; storage remains behind internal APIs."""

import os
from uuid import UUID

from fastapi import HTTPException
from fastmcp import Client
from pydantic import TypeAdapter
from v1_models import Actor, InvestigationRecord


async def read_history(who: Actor, tid: UUID | None = None) -> list[InvestigationRecord] | InvestigationRecord:
    url = os.getenv("BUSINESS_MCP_URL", "http://business-mcp:8000/mcp").rstrip("/")
    if not url.endswith("/mcp"):
        url += "/mcp"
    args = {"user_name": who.name, "user_role": who.role}
    if tid is not None:
        args["task_id"] = str(tid)
    try:
        async with Client(url, timeout=30) as client:
            result = await client.call_tool(
                "get_investigation" if tid else "list_investigations", args,
            )
        data = result.structured_content
        if tid:
            return InvestigationRecord.model_validate(data)
        return TypeAdapter(list[InvestigationRecord]).validate_python(data["result"])
    except Exception as exc:
        raise HTTPException(502, "조사 이력 조회에 실패했습니다. 다시 시도해 주세요.") from exc
