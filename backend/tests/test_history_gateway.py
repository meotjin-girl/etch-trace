"""Real MCP dispatch covers the history gateway without a database."""

import anyio
import pytest
from fastapi import HTTPException
from fastmcp import Client, FastMCP
from v1_history import read_history
from v1_models import Actor


def test_history_list_forwards_identity_and_decodes_array(monkeypatch):
    server = FastMCP("history")
    seen = []

    @server.tool
    def list_investigations(user_name: str, user_role: str) -> list[dict]:
        seen.append((user_name, user_role))
        return []

    monkeypatch.setattr("v1_history.Client", lambda *args, **kwargs: Client(server))
    assert anyio.run(read_history, Actor("작업자", "worker")) == []
    assert seen == [("작업자", "worker")]


def test_history_gateway_failure_is_not_an_empty_list(monkeypatch):
    server = FastMCP("history")

    @server.tool
    def list_investigations(user_name: str, user_role: str) -> list[dict]:
        raise ValueError("backend unavailable")

    monkeypatch.setattr("v1_history.Client", lambda *args, **kwargs: Client(server))
    with pytest.raises(HTTPException) as failure:
        anyio.run(read_history, Actor("reader", "engineer"))
    assert failure.value.status_code == 502


def test_history_detail_decodes_snapshot_and_forwards_task_id(monkeypatch):
    from uuid import uuid4
    server = FastMCP("history")
    tid = str(uuid4())
    seen = []

    @server.tool
    def get_investigation(task_id: str, user_name: str, user_role: str) -> dict:
        seen.append((task_id, user_name, user_role))
        return {
            "id": tid, "user_name": "owner", "user_role": "worker",
            "question": "endpoint 지연", "status": "DONE", "report": {"summary": "승인"},
            "created_at": "2026-10-20T00:00:00Z", "updated_at": "2026-10-20T00:00:00Z",
            "approved_by": "engineer", "approved_role": "engineer",
            "approved_at": "2026-10-20T00:00:00Z", "event_time": None, "lot_id": "LOT-1",
        }


    monkeypatch.setattr("v1_history.Client", lambda *args, **kwargs: Client(server))
    from uuid import UUID
    result = anyio.run(read_history, Actor("owner", "worker"), UUID(tid))
    assert result.report.summary == "승인"
    assert not ({"messages", "reviews", "events", "command_id"} & result.model_dump().keys())
    assert seen == [(tid, "owner", "worker")]
