"""TRACE backend v1: task ownership, event replay and HTTP agent coordination."""

import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

import anyio
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from v1_auth import Authenticator, internal
from v1_commands import accept_message, accept_review, callback
from v1_dispatch import dispatch
from v1_models import (
    Actor,
    ApprovalInput,
    Callback,
    Detail,
    Event,
    MessageInput,
    Settings,
    Task,
    TaskInput,
)
from v1_store import Row, Store


@dataclass(frozen=True, slots=True)
class Runtime:
    store: Store
    settings: Settings
    authenticator: Authenticator


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime: Runtime | None = None

    def current() -> Runtime:
        assert runtime is not None, "Application lifespan has not started"
        return runtime

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        nonlocal runtime
        _ = load_dotenv(Path(__file__).parent.parent / ".env")
        config = settings or Settings(
            os.getenv("DATABASE_URL", "postgresql://trace:trace@localhost:5432/trace"),
            os.getenv("AGENT_URL", "http://agent:8001"),
            os.getenv("INTERNAL_API_KEY", "dev-internal-key"),
            keycloak_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080/auth"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM", "trace"),
            keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID", "trace-web"),
            keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE", "trace-api"),
            keycloak_jwks_url=os.getenv("KEYCLOAK_JWKS_URL", ""),
        )
        if not config.internal_api_key:
            raise RuntimeError("INTERNAL_API_KEY must not be empty")
        store = Store(config.database_url)
        runtime = Runtime(store, config, Authenticator(config))
        application.state.settings = config
        application.state.store = store
        try:
            await anyio.to_thread.run_sync(store.initialize)
            yield
        finally:
            await anyio.to_thread.run_sync(store.pool.close)
            runtime = None

    app = FastAPI(title="TRACE Backend", version="1.0.0", lifespan=lifespan)

    def actor(request: Request) -> Actor:
        return current().authenticator.authenticate(request.headers.get("authorization"))

    @app.get("/api/auth/config")
    def auth_config() -> dict[str, str]:
        config = current().settings
        return {
            "url": config.keycloak_url,
            "realm": config.keycloak_realm,
            "clientId": config.keycloak_client_id,
        }

    def authenticate_internal(request: Request) -> None:
        internal(
            current().settings.internal_api_key,
            request.headers.get("x-internal-key") or request.headers.get("x-internal-api-key"),
        )

    @app.post("/api/ai/tasks", status_code=202)
    def create_task(
        body: TaskInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(actor)],
    ) -> dict[str, str]:
        store = current().store
        tid = store.create(body.question, who)
        bg.add_task(dispatch, store, current().settings, tid, {"question": body.question})
        return {"taskId": str(tid)}

    @app.get("/api/ai/tasks", dependencies=[Depends(actor)])
    def list_tasks() -> list[Task]:
        return current().store.listing()

    @app.get("/api/ai/tasks/{tid}", dependencies=[Depends(actor)])
    def get_task(tid: UUID) -> Detail:
        return current().store.detail(tid)

    @app.post("/api/ai/tasks/{tid}/messages", status_code=202)
    def message(
        tid: UUID,
        body: MessageInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(actor)],
    ) -> dict[str, str]:
        store = current().store
        command_id = accept_message(store, tid, body.text, who)
        bg.add_task(
            dispatch,
            store,
            current().settings,
            tid,
            {"resume": {"text": body.text}},
            command_id,
        )
        return {"taskId": str(tid)}

    @app.post("/api/ai/tasks/{tid}/approval", status_code=202)
    def approval(
        tid: UUID,
        body: ApprovalInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(actor)],
    ) -> dict[str, str]:
        store = current().store
        command_id = accept_review(store, tid, body, who)
        bg.add_task(
            dispatch,
            store,
            current().settings,
            tid,
            {"resume": {"action": body.action, "comment": body.comment, "by": who.name}},
            command_id,
        )
        return {"taskId": str(tid)}

    @app.get("/api/ai/tasks/{tid}/events", dependencies=[Depends(actor)])
    def events(
        tid: UUID,
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Event]:
        return current().store.events(tid, after)[0]

    @app.get("/api/ai/tasks/{tid}/stream")
    async def stream(
        tid: UUID,
        request: Request,
        who: Annotated[Actor, Depends(actor)],
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> StreamingResponse:
        try:
            cursor = max(after, int(request.headers.get("last-event-id", "0")))
            if cursor < 0:
                raise ValueError("negative cursor")
        except ValueError as exc:
            raise HTTPException(422, "Invalid Last-Event-ID") from exc
        store = current().store
        # Authenticate the resource before response headers are sent.
        _ = await anyio.to_thread.run_sync(store.events, tid, cursor)

        async def generate() -> AsyncGenerator[str]:
            last = cursor
            while not await request.is_disconnected():
                if datetime.now(UTC).timestamp() >= who.expires_at:
                    return
                rows, status = await anyio.to_thread.run_sync(store.events, tid, last)
                for row in rows:
                    last = row.seq
                    data = json.dumps(
                        {**row.payload, "at": row.created_at.isoformat()},
                        ensure_ascii=False,
                        default=str,
                    )
                    yield f"id: {last}\nevent: {row.type}\ndata: {data}\n\n"
                if status in {"DONE", "INCOMPLETE", "FAILED"}:
                    return
                if not rows:
                    yield ": keep-alive\n\n"
                await anyio.sleep(0.5)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/internal/tasks/{tid}/events", dependencies=[Depends(authenticate_internal)])
    def agent_event(tid: UUID, body: Callback, request: Request) -> dict[str, bool]:
        scope = request.headers.get("x-command-id")
        if not scope:
            raise HTTPException(422, "X-Command-ID is required")
        try:
            command_id = UUID(scope)
        except ValueError as exc:
            raise HTTPException(422, "Invalid X-Command-ID") from exc
        accepted = callback(current().store, tid, body, command_id)
        return {"accepted": accepted, "duplicate": not accepted}

    @app.get("/internal/cases", dependencies=[Depends(authenticate_internal)])
    def cases() -> list[Row]:
        return current().store.cases()

    return app


app = create_app()
