"""Internal HTTP runner. The backend owns public state and failure handling."""

import hmac
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Annotated
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.config import get_config
from langgraph.types import Command

from .evidence import MCPEvidenceProvider
from .graph import build_graph
from .models import Clarification, Event, InitialRequest, ResumeRequest


@dataclass(frozen=True, slots=True)
class Callback:
    backend_url: str
    internal_key: str

    def __call__(self, task_id: str, event: Event) -> None:
        """HTTP errors propagate so the backend cannot mistake failure for success."""
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
                Callback(os.environ["BACKEND_URL"], key),
            )
            yield

    app = FastAPI(title="TRACE Agent", version="1.0.0", lifespan=lifespan)

    @app.post("/internal/tasks/{task_id}/run")
    def run(
        task_id: UUID,
        body: InitialRequest | ResumeRequest,
        x_command_id: Annotated[UUID, Header()],
        x_internal_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, str]:
        key = app.state.internal_key
        if not x_internal_key or not hmac.compare_digest(x_internal_key, key):
            raise HTTPException(status_code=403, detail="Invalid internal key")
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
                    graph.invoke({"task_id": task, "question": question}, config)
                case ResumeRequest(resume=answer):
                    if not snapshot.interrupts:
                        raise HTTPException(status_code=409, detail="Task is not waiting for input")
                    expected = "clarification" if isinstance(answer, Clarification) else "review"
                    if snapshot.interrupts[0].value["kind"] != expected:
                        raise HTTPException(
                            status_code=409, detail="Resume does not match waiting state",
                        )
                    graph.invoke(Command(resume=answer.model_dump()), config)
            snapshot = graph.get_state(config)
            if snapshot.interrupts:
                return {"status": "interrupted", "waiting": snapshot.interrupts[0].value["kind"]}
            return {"status": "completed"}

    return app


app = create_app()
