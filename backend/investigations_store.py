"""Revision-checked live writes and one immutable approval on the shared pool."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from investigations_models import (
    Approval,
    ApprovalInput,
    Investigation,
    InvestigationSummary,
    LiveInput,
    LiveResult,
)
from psycopg import Connection
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from v1_models import Actor
from v1_store import DatabaseRow


class InvestigationsStore:
    def __init__(self, pool: ConnectionPool[Connection[DatabaseRow]]) -> None:
        self.pool: ConnectionPool[Connection[DatabaseRow]] = pool

    def initialize(self) -> None:
        with self.pool.connection() as conn:
            _ = conn.execute(Path(__file__).with_name("investigations_schema.sql").read_bytes())

    def detail(self, thread_id: UUID) -> Investigation:
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT *, id AS thread_id FROM v1_live_investigations WHERE id=%s",
                (thread_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Investigation not found")
        return Investigation.model_validate(row)

    def listing(self) -> list[InvestigationSummary]:
        with self.pool.connection() as conn:
            rows = conn.execute(
                """SELECT id, id AS thread_id, alert->>'tool_id' AS tool_id,
                   alert->>'chamber_id' AS chamber_id, alert->>'lot_id' AS lot_id,
                   summary, revision, jsonb_array_length(candidates) AS candidate_count,
                   approval->>'approved_at' AS approved_at, created_at, updated_at
                   FROM v1_live_investigations ORDER BY updated_at DESC, id"""
            ).fetchall()
        return [InvestigationSummary.model_validate(row) for row in rows]

    def upsert(self, thread_id: UUID, body: LiveInput) -> LiveResult:
        payload = body.model_dump(mode="json")
        with self.pool.connection() as conn:
            if body.base_revision == 0:
                row = conn.execute(
                    """INSERT INTO v1_live_investigations
                       (id, alert, summary, candidates, revision) VALUES (%s,%s,%s,%s,1)
                       ON CONFLICT (id) DO NOTHING RETURNING id, id AS thread_id, revision""",
                    (
                        thread_id,
                        Jsonb(payload["alert"]),
                        body.summary,
                        Jsonb(payload["candidates"]),
                    ),
                ).fetchone()
                if row is None:
                    raise HTTPException(409, "Stale investigation revision")
                return LiveResult.model_validate(row)

            row = conn.execute(
                "SELECT *, id AS thread_id FROM v1_live_investigations WHERE id=%s FOR UPDATE",
                (thread_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(409, "First investigation write requires base_revision 0")
            current = Investigation.model_validate(row)
            if current.revision != body.base_revision:
                raise HTTPException(409, "Stale investigation revision")
            if current.alert != body.alert:
                raise HTTPException(422, "Investigation alert is immutable")
            _ = conn.execute(
                """UPDATE v1_live_investigations SET summary=%s, candidates=%s,
                   revision=revision+1, updated_at=clock_timestamp() WHERE id=%s""",
                (body.summary, Jsonb(payload["candidates"]), thread_id),
            )
            return LiveResult(id=thread_id, thread_id=thread_id, revision=current.revision + 1)

    def approve(self, thread_id: UUID, body: ApprovalInput, actor: Actor) -> Approval:
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT *, id AS thread_id FROM v1_live_investigations WHERE id=%s FOR UPDATE",
                (thread_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Investigation not found")
            current = Investigation.model_validate(row)
            if current.approval is not None:
                raise HTTPException(409, "Investigation already approved")
            if current.revision != body.expected_revision:
                raise HTTPException(409, "Stale investigation revision")
            candidate = next(
                (item for item in current.candidates if item.id == body.candidate_id), None
            )
            if candidate is None:
                raise HTTPException(422, "Candidate does not belong to this revision")
            approval = Approval(
                revision=current.revision,
                candidate=candidate,
                approved_by_id=actor.subject,
                approved_by=actor.name,
                approved_at=datetime.now(UTC),
                comment=body.comment,
            )
            _ = conn.execute(
                """UPDATE v1_live_investigations SET approval=%s,
                   updated_at=clock_timestamp() WHERE id=%s""",
                (Jsonb(approval.model_dump(mode="json")), thread_id),
            )
            return approval
