"""Internal HTTP runner. The backend owns public state and failure handling."""

import hmac
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Annotated, Literal
from urllib.parse import unquote
from urllib.request import Request, urlopen
from uuid import UUID

import anyio
from fastapi import FastAPI, Header, HTTPException
from fastmcp import Client
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.config import get_config
from langgraph.types import Command

from .evidence import MCPEvidenceProvider, mcp_url
from .graph import build_graph
from .models import Clarification, Event, InitialRequest, Requester, ResumeRequest


@dataclass(frozen=True, slots=True)
class Callback:
    backend_url: str
    internal_key: str
    business_url: str | None = None

    def __call__(self, task_id: str, event: Event) -> None:
        """HTTP errors propagate so the backend cannot mistake failure for success."""
        if event.type == "DONE" and self.business_url:
            anyio.run(
                self._save_investigation,
                task_id,
                event,
                get_config().get("configurable", {})["command_id"],
            )
            return
        request = Request(
            f"{self.backend_url.rstrip('/')}/internal/tasks/{task_id}/events",
            data=event.model_dump_json().encode(),
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": self.internal_key,
                "X-Command-ID": get_config().get("configurable", {})["command_id"],
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            response.read()

    async def _save_investigation(self, task_id: str, event: Event, command_id: str) -> None:
        assert self.business_url is not None
        async with Client(mcp_url(self.business_url)) as client:
            await client.call_tool(
                "save_investigation",
                {
                    "task_id": task_id,
                    "command_id": command_id,
                    "event_id": event.event_id,
                    "payload": event.payload,
                },
            )


def create_app() -> FastAPI:
    """Open the checkpoint connection only during application lifespan."""
    locks: dict[str, Lock] = {}
    locks_guard = Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        key = os.environ["INTERNAL_API_KEY"]
        if not key:
            raise RuntimeError("INTERNAL_API_KEY must not be empty")
        with PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]) as saver:
            saver.setup()
            app.state.internal_key = key
            app.state.graph = build_graph(
                saver,
                MCPEvidenceProvider(os.environ["BUSINESS_MCP_URL"], os.environ["RAG_MCP_URL"]),
                Callback(os.environ["BACKEND_URL"], key, os.environ["BUSINESS_MCP_URL"]),
            )
            yield

    app = FastAPI(title="TRACE Agent", version="1.0.0", lifespan=lifespan)

    @app.post("/internal/tasks/{task_id}/run")
    def run(
        task_id: UUID,
        body: InitialRequest | ResumeRequest,
        x_command_id: Annotated[UUID, Header()],
        x_internal_key: Annotated[str | None, Header()] = None,
        x_requester_name: Annotated[str | None, Header()] = None,
        x_requester_role: Annotated[
            Literal["user", "worker", "engineer", "admin"] | None, Header()
        ] = None,
    ) -> dict[str, str]:
        key = app.state.internal_key
        if not x_internal_key or not hmac.compare_digest(x_internal_key, key):
            raise HTTPException(status_code=403, detail="Invalid internal key")
        if (x_requester_name is None) != (x_requester_role is None):
            raise HTTPException(status_code=422, detail="Incomplete requester identity")
        requester = (
            Requester(name=unquote(x_requester_name), role=x_requester_role)
            if x_requester_name is not None and x_requester_role is not None
            else None
        )
        task = str(task_id)
        # One uvicorn worker owns all thread invocations (see Dockerfile).
        # Lock covers checkpoint read, validation, and the entire graph invocation.
        with locks_guard:
            thread_lock = locks.setdefault(task, Lock())
        with thread_lock:
            graph = app.state.graph
            config = {
                "configurable": {"thread_id": task, "command_id": str(x_command_id)},
                "recursion_limit": 100,
            }
            snapshot = graph.get_state(config)
            match body:
                case InitialRequest(question=question):
                    if snapshot.values:
                        raise HTTPException(status_code=409, detail="Task already initialized")
                    graph.invoke(
                        {
                            "task_id": task,
                            "question": question,
                            "requester": requester,
                        },
                        config,
                    )
                case ResumeRequest(resume=answer):
                    if not snapshot.interrupts:
                        raise HTTPException(status_code=409, detail="Task is not waiting for input")
                    expected = "clarification" if isinstance(answer, Clarification) else "review"
                    if snapshot.interrupts[0].value["kind"] != expected:
                        raise HTTPException(
                            status_code=409,
                            detail="Resume does not match waiting state",
                        )
                    graph.invoke(Command(resume=answer.model_dump()), config)
            snapshot = graph.get_state(config)
            if snapshot.interrupts:
                return {"status": "interrupted", "waiting": snapshot.interrupts[0].value["kind"]}
            return {"status": "completed"}

    return app


app = create_app()
