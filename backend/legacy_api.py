"""Legacy v1 HTTP routes, with the original stream clock supplied by main."""

import json
from collections.abc import AsyncGenerator, Callable
from typing import Annotated
from uuid import UUID

import anyio
from api_dependencies import Dependencies
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from v1_commands import accept_message, accept_review, callback
from v1_dispatch import dispatch
from v1_models import (
    Actor,
    ApprovalInput,
    Callback,
    Detail,
    Event,
    InvestigationRecord,
    MessageInput,
    Task,
    TaskInput,
)
from v1_sop import Sop, SopSummary
from v1_sop import document as sop_document
from v1_sop import summaries as sop_summaries
from v1_store import Row


def router(dependencies: Dependencies, clock: Callable[[], float]) -> APIRouter:
    api = APIRouter()

    @api.get("/internal/investigations", dependencies=[Depends(dependencies.internal)])
    def internal_history() -> list[InvestigationRecord]:
        return dependencies.current().store.investigations()

    @api.get("/internal/investigations/{tid}", dependencies=[Depends(dependencies.internal)])
    def internal_history_detail(tid: UUID) -> InvestigationRecord:
        return dependencies.current().store.investigation(tid)

    # Screen history reads come straight from the store; MCP tools stay agent-only.
    @api.get("/api/ai/investigations", dependencies=[Depends(dependencies.actor)])
    def list_history() -> list[InvestigationRecord]:
        return dependencies.current().store.investigations()

    @api.get("/api/ai/investigations/{tid}", dependencies=[Depends(dependencies.actor)])
    def history_detail(tid: UUID) -> InvestigationRecord:
        return dependencies.current().store.investigation(tid)

    @api.get("/api/sops", dependencies=[Depends(dependencies.actor)])
    def list_sops() -> list[SopSummary]:
        return sop_summaries(dependencies.current().settings.sop_dir)

    @api.get("/api/sops/{doc_id}", dependencies=[Depends(dependencies.actor)])
    def get_sop(doc_id: str) -> Sop:
        return sop_document(dependencies.current().settings.sop_dir, doc_id)

    @api.post("/api/ai/tasks", status_code=202)
    def create_task(
        body: TaskInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(dependencies.actor)],
    ) -> dict[str, str]:
        store = dependencies.current().store
        tid = store.create(body.question, who)
        bg.add_task(
            dispatch,
            store,
            dependencies.current().settings,
            tid,
            {"role": "user", "content": body.question},
        )
        return {"taskId": str(tid)}

    @api.get("/api/ai/tasks", dependencies=[Depends(dependencies.actor)])
    def list_tasks() -> list[Task]:
        return dependencies.current().store.listing()

    @api.get("/api/ai/tasks/{tid}", dependencies=[Depends(dependencies.actor)])
    def get_task(tid: UUID) -> Detail:
        return dependencies.current().store.detail(tid)

    @api.post("/api/ai/tasks/{tid}/messages", status_code=202)
    def message(
        tid: UUID,
        body: MessageInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(dependencies.actor)],
    ) -> dict[str, str]:
        store = dependencies.current().store
        command_id = accept_message(store, tid, body.text, who)
        bg.add_task(
            dispatch,
            store,
            dependencies.current().settings,
            tid,
            {"resume": {"text": body.text}},
            command_id,
        )
        return {"taskId": str(tid)}

    @api.post("/api/ai/tasks/{tid}/approval", status_code=202)
    def approval(
        tid: UUID,
        body: ApprovalInput,
        bg: BackgroundTasks,
        who: Annotated[Actor, Depends(dependencies.actor)],
    ) -> dict[str, str]:
        store = dependencies.current().store
        command_id = accept_review(store, tid, body, who)
        bg.add_task(
            dispatch,
            store,
            dependencies.current().settings,
            tid,
            {"resume": {"action": body.action, "comment": body.comment, "by": who.name}},
            command_id,
        )
        return {"taskId": str(tid)}

    @api.get("/api/ai/tasks/{tid}/events", dependencies=[Depends(dependencies.actor)])
    def events(
        tid: UUID,
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Event]:
        return dependencies.current().store.events(tid, after)[0]

    @api.get("/api/ai/tasks/{tid}/stream")
    async def stream(
        tid: UUID,
        request: Request,
        who: Annotated[Actor, Depends(dependencies.actor)],
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> StreamingResponse:
        try:
            cursor = max(after, int(request.headers.get("last-event-id", "0")))
            if cursor < 0:
                raise ValueError("negative cursor")
        except ValueError as exc:
            raise HTTPException(422, "Invalid Last-Event-ID") from exc
        store = dependencies.current().store
        # Authenticate the resource before response headers are sent.
        _ = await anyio.to_thread.run_sync(store.events, tid, cursor)

        async def generate() -> AsyncGenerator[str]:
            last = cursor
            while not await request.is_disconnected():
                if clock() >= who.expires_at:
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

    @api.post("/internal/tasks/{tid}/events", dependencies=[Depends(dependencies.internal)])
    def agent_event(tid: UUID, body: Callback, request: Request) -> dict[str, bool]:
        scope = request.headers.get("x-command-id")
        if not scope:
            raise HTTPException(422, "X-Command-ID is required")
        try:
            command_id = UUID(scope)
        except ValueError as exc:
            raise HTTPException(422, "Invalid X-Command-ID") from exc
        accepted = callback(dependencies.current().store, tid, body, command_id)
        return {"accepted": accepted, "duplicate": not accepted}

    @api.post("/internal/tasks/{tid}/investigation", dependencies=[Depends(dependencies.internal)])
    def save_investigation(tid: UUID, body: Callback, request: Request) -> dict[str, bool]:
        if body.type != "DONE":
            raise HTTPException(422, "Investigation save requires DONE")
        return agent_event(tid, body, request)

    @api.get("/internal/cases", dependencies=[Depends(dependencies.internal)])
    def cases() -> list[Row]:
        return dependencies.current().store.cases()

    return api
