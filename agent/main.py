"""Internal HTTP runner for the single checkpointed ReAct agent."""

import hmac
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Annotated, Literal
from urllib.parse import unquote
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver

from .evidence import MCPEvidenceProvider
from .models import AgentMessage, Clarification, InitialRequest, Requester, ResumeRequest, Review
from .react_agent import (
    build_react_graph,
    latest_response,
    prepare_request,
    selection_from_messages,
)


@dataclass(frozen=True, slots=True)
class Settings:
    internal_key: str
    database_url: str
    business_url: str
    rag_url: str
    physics_url: str


def create_app() -> FastAPI:
    """Open the PostgreSQL checkpointer at startup; task ID is the conversation ID."""
    locks: dict[str, Lock] = {}
    locks_guard = Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = Settings(
            internal_key=os.environ["INTERNAL_API_KEY"],
            database_url=os.environ["DATABASE_URL"],
            business_url=os.environ["BUSINESS_MCP_URL"],
            rag_url=os.environ["RAG_MCP_URL"],
            physics_url=os.environ["PHYSICS_MCP_URL"],
        )
        if not settings.internal_key:
            raise RuntimeError("INTERNAL_API_KEY must not be empty")
        with PostgresSaver.from_conn_string(settings.database_url) as saver:
            saver.setup()
            app.state.internal_key = settings.internal_key
            app.state.graph = build_react_graph(
                saver,
                MCPEvidenceProvider(
                    settings.business_url,
                    settings.rag_url,
                    settings.physics_url,
                ),
            )
            yield

    app = FastAPI(title="TRACE ReAct Agent", version="1.0.0", lifespan=lifespan)

    @app.post("/internal/tasks/{task_id}/run")
    def run(
        task_id: UUID,
        body: AgentMessage | InitialRequest | ResumeRequest,
        x_command_id: Annotated[UUID, Header()],
        x_internal_key: Annotated[str | None, Header()] = None,
        x_requester_name: Annotated[str | None, Header()] = None,
        x_requester_role: Annotated[
            Literal["user", "worker", "engineer", "admin"] | None, Header()
        ] = None,
    ) -> dict[str, str]:
        if not x_internal_key or not hmac.compare_digest(x_internal_key, app.state.internal_key):
            raise HTTPException(status_code=403, detail="Invalid internal key")
        if (x_requester_name is None) != (x_requester_role is None):
            raise HTTPException(status_code=422, detail="Incomplete requester identity")
        requester = (
            Requester(name=unquote(x_requester_name), role=x_requester_role)
            if x_requester_name is not None and x_requester_role is not None
            else None
        )

        match body:
            case AgentMessage(role=role, content=content):
                user_role, user_content = role, content
            case InitialRequest(question=question):
                user_role, user_content = "user", question
            case ResumeRequest(resume=Clarification(text=text)):
                user_role, user_content = "user", text
            case ResumeRequest(resume=Review(action="approve")):
                user_role = "user"
                user_content = "현재 대화에서 제시된 최종 원인-조치 세트를 승인합니다."
            case ResumeRequest(resume=Review(action="revise", comment=comment)):
                user_role = "user"
                user_content = "기존 조사 결과를 수정해 주세요. " + comment
            case _:
                raise HTTPException(status_code=422, detail="Unsupported agent request")

        graph = app.state.graph
        config = {
            "configurable": {"thread_id": str(task_id), "command_id": str(x_command_id)},
            "recursion_limit": 100,
        }
        with locks_guard:
            thread_lock = locks.setdefault(str(task_id), Lock())
        with thread_lock:
            result = graph.invoke(
                prepare_request(user_role, user_content, requester),
                config,
            )
        messages = result.get("messages", [])
        selected = selection_from_messages(messages)
        return {
            "status": "selected" if selected else "completed",
            "response": latest_response(messages),
        }

    return app


app = create_app()
