"""Transactional persistence; every event writer first locks its task row."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import JsonValue
from v1_models import Actor, CaseData, Detail, Event, Status, Task

type Row = dict[str, JsonValue]
type DatabaseRow = dict[str, JsonValue | UUID]


class Store:
    """Own a pool opened by the application lifespan, never by import."""

    def __init__(self, database_url: str) -> None:
        self.pool: ConnectionPool[Connection[DatabaseRow]] = ConnectionPool(
            database_url,
            open=False,
            kwargs={"row_factory": dict_row},
            min_size=1,
            max_size=10,
            timeout=10,
        )

    def initialize(self) -> None:
        self.pool.open(wait=True)
        with self.pool.connection() as conn:
            _ = conn.execute(Path(__file__).with_name("v1_schema.sql").read_bytes())
            rows = conn.execute(
                """SELECT * FROM v1_tasks WHERE status IN ('RUNNING','QUEUED')
                   ORDER BY id FOR UPDATE"""
            ).fetchall()
            for row in rows:
                tid = Task.model_validate(row).id
                self.status(conn, tid, "FAILED")
                self.emit(conn, tid, "FAILED", {"error": "Backend interrupted"})

    @contextmanager
    def locked(self, tid: UUID) -> Generator[tuple[Connection[DatabaseRow], Task]]:
        with self.pool.connection() as conn:
            row = conn.execute("SELECT * FROM v1_tasks WHERE id=%s FOR UPDATE", (tid,)).fetchone()
            if row is None:
                raise HTTPException(404, "Task not found")
            yield conn, Task.model_validate(row)

    @staticmethod
    def status(
        conn: Connection[DatabaseRow],
        tid: UUID,
        status: Status,
        report: Row | None = None,
    ) -> None:
        _ = conn.execute(
            """UPDATE v1_tasks SET status=%s, report=COALESCE(%s,report),
               updated_at=now() WHERE id=%s""",
            (status, Jsonb(report) if report is not None else None, tid),
        )

    @staticmethod
    def emit(
        conn: Connection[DatabaseRow],
        tid: UUID,
        kind: str,
        payload: Row,
        event_id: str | None = None,
    ) -> None:
        _ = conn.execute(
            """INSERT INTO v1_events(task_id,seq,type,payload,event_id)
               SELECT %s,COALESCE(MAX(seq),0)+1,%s,%s,%s FROM v1_events WHERE task_id=%s""",
            (tid, kind, Jsonb(payload), event_id, tid),
        )

    @staticmethod
    def message(
        conn: Connection[DatabaseRow],
        tid: UUID,
        text: str,
        actor: Actor | None,
        role: str,
    ) -> None:
        _ = conn.execute(
            """INSERT INTO v1_messages(task_id,role,text,user_name,user_role,user_id)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                tid,
                role,
                text,
                actor.name if actor else "agent",
                actor.role if actor else "agent",
                actor.subject if actor else None,
            ),
        )

    def create(self, question: str, actor: Actor) -> UUID:
        tid = uuid4()
        with self.pool.connection() as conn:
            _ = conn.execute(
                """INSERT INTO v1_tasks(id,user_name,user_role,user_id,question,status,command_id)
                   VALUES (%s,%s,%s,%s,%s,'QUEUED',%s)""",
                (tid, actor.name, actor.role, actor.subject, question, uuid4()),
            )
            self.message(conn, tid, question, actor, "user")
            self.emit(conn, tid, "QUEUED", {"by": actor.name, "user_id": actor.subject})
        return tid

    def listing(self) -> list[Task]:
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM v1_tasks ORDER BY created_at DESC,id",
            ).fetchall()
            return [Task.model_validate(row) for row in rows]

    def detail(self, tid: UUID) -> Detail:
        with self.locked(tid) as (conn, row):
            data = row.model_dump()
            data["messages"] = conn.execute(
                "SELECT * FROM v1_messages WHERE task_id=%s ORDER BY id", (tid,)
            ).fetchall()
            data["events"] = conn.execute(
                "SELECT * FROM v1_events WHERE task_id=%s ORDER BY seq", (tid,)
            ).fetchall()
            data["reviews"] = conn.execute(
                "SELECT * FROM v1_reviews WHERE task_id=%s ORDER BY id", (tid,)
            ).fetchall()
            data["investigation"] = conn.execute(
                "SELECT * FROM v1_investigations WHERE task_id=%s", (tid,)
            ).fetchone()
            return Detail.model_validate(data)

    def events(self, tid: UUID, after: int) -> tuple[list[Event], Status]:
        with self.locked(tid) as (conn, row):
            rows = conn.execute(
                "SELECT * FROM v1_events WHERE task_id=%s AND seq>%s ORDER BY seq",
                (tid, after),
            ).fetchall()
            return [Event.model_validate(item) for item in rows], row.status

    def cases(self) -> list[Row]:
        with self.pool.connection() as conn:
            rows = conn.execute("SELECT data FROM etch_cases ORDER BY id").fetchall()
            return [CaseData.model_validate(row).data for row in rows]
