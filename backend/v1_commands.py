"""Atomic command acceptance and conditional agent callback handling."""

from uuid import UUID, uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb
from pydantic import ValidationError
from v1_models import Actor, ApprovalInput, Callback, Report, Status
from v1_store import Store


def accept_message(store: Store, tid: UUID, text: str, actor: Actor) -> UUID:
    with store.locked(tid) as (conn, row):
        store.access(row, actor, owner=True)
        if row.status != "WAITING_INPUT":
            raise HTTPException(409, "Task is not waiting for input")
        store.status(conn, tid, "RUNNING")
        command_id = uuid4()
        _ = conn.execute("UPDATE v1_tasks SET command_id=%s WHERE id=%s", (command_id, tid))
        store.message(conn, tid, text, actor, "user")
        store.emit(conn, tid, "MESSAGE", {"text": text, "by": actor.name})
        store.emit(conn, tid, "RUNNING", {"by": actor.name})
        return command_id


def accept_review(store: Store, tid: UUID, body: ApprovalInput, actor: Actor) -> UUID:
    if actor.role != "engineer":
        raise HTTPException(403, "Only engineers may approve or revise")
    with store.locked(tid) as (conn, row):
        if row.status != "WAITING_APPROVAL":
            raise HTTPException(409, "Task is not waiting for approval")
        _ = conn.execute(
            """INSERT INTO v1_reviews(task_id,action,comment,user_name,user_role,
               report,event_time,lot_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (tid, body.action, body.comment, actor.name, actor.role,
             Jsonb(row.report.model_dump(mode="json") if row.report else None),
             body.event_time, body.lot_id),
        )
        store.status(conn, tid, "RUNNING")
        command_id = uuid4()
        _ = conn.execute("UPDATE v1_tasks SET command_id=%s WHERE id=%s", (command_id, tid))
        store.emit(conn, tid, "REVIEWED", {
            **body.model_dump(mode="json"), "by": actor.name, "role": actor.role,
        })
        store.emit(conn, tid, "RUNNING", {"by": actor.name})
        return command_id


def start(store: Store, tid: UUID) -> UUID | None:
    with store.locked(tid) as (conn, row):
        if row.status != "QUEUED":
            return None
        store.status(conn, tid, "RUNNING")
        store.emit(conn, tid, "RUNNING", {})
        return row.command_id


def dispatch_failed(store: Store, tid: UUID, command_id: UUID, error: str) -> None:
    with store.locked(tid) as (conn, row):
        if row.status == "RUNNING" and row.command_id == command_id:
            store.status(conn, tid, "FAILED")
            store.emit(conn, tid, "FAILED", {"error": error})


def callback(store: Store, tid: UUID, body: Callback, command_id: UUID) -> bool:
    """Return False for a repeated event ID; all mutations share one transaction."""
    payload = body.payload
    event_id = f"{command_id}:{body.event_id}"
    report = None
    if body.type in {"APPROVAL_REQUIRED", "DONE"}:
        try:
            report = Report.model_validate(payload.get("report")).model_dump(mode="json")
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
    with store.locked(tid) as (conn, row):
        previous = conn.execute(
            "SELECT type,payload FROM v1_events WHERE task_id=%s AND event_id=%s",
            (tid, event_id),
        ).fetchone()
        if previous:
            if previous["type"] != body.type or previous["payload"] != payload:
                raise HTTPException(409, "event_id already has different content")
            return False
        if row.command_id != command_id:
            raise HTTPException(409, "Stale command callback")
        if row.status != "RUNNING":
            raise HTTPException(409, "Task is not running")
        statuses: dict[str, Status] = {
            "QUESTION": "WAITING_INPUT", "APPROVAL_REQUIRED": "WAITING_APPROVAL",
            "DONE": "DONE", "INCOMPLETE": "INCOMPLETE", "FAILED": "FAILED",
        }
        status = statuses.get(body.type, "RUNNING")
        if body.type == "QUESTION":
            text = payload.get("text") or payload.get("question")
            if not isinstance(text, str) or not text.strip():
                raise HTTPException(422, "QUESTION requires payload.text")
            store.message(conn, tid, text, None, "assistant")
        if body.type == "DONE":
            review = conn.execute(
                "SELECT * FROM v1_reviews WHERE task_id=%s ORDER BY id DESC LIMIT 1",
                (tid,),
            ).fetchone()
            if not review or review["action"] != "approve" or review["user_role"] != "engineer":
                raise HTTPException(409, "Investigation requires an engineer approval")
            if review["report"] != report:
                raise HTTPException(409, "Report differs from approved snapshot")
        store.status(conn, tid, status, report)
        store.emit(conn, tid, body.type, payload, event_id)
        if body.type == "DONE":
            _ = conn.execute(
                """INSERT INTO v1_investigations(task_id,review_id,report,approved_by,
                   approved_role,event_time,lot_id,approved_at)
                   SELECT task_id,id,report,user_name,user_role,event_time,lot_id,created_at
                   FROM (SELECT * FROM v1_reviews WHERE task_id=%s ORDER BY id DESC LIMIT 1) r
                   WHERE action='approve'""", (tid,),
            )
    return True
