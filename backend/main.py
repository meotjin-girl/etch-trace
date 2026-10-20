"""TRACE Agent 서버. /api/ai/** 경로와 응답은 PDF API 계약(p.60) 그대로 —
나중에 Spring Boot가 같은 경로를 넘겨받아도 프론트는 바뀌지 않는다.
인증은 목업: X-User-Name / X-User-Role 헤더 (Supabase Auth로 교체 예정)."""
import asyncio
import json
import time
import uuid
from typing import Literal
from urllib.parse import unquote

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

import db
import graph

ROLES = {"worker", "engineer", "admin"}
db.init()
app = FastAPI(title="TRACE Agent")


def user(name: str | None, role: str | None, allowed=ROLES):
    if not name or role not in ROLES:
        raise HTTPException(401, "로그인이 필요합니다")
    if role not in allowed:
        raise HTTPException(403, f"{role} 역할은 이 작업을 할 수 없습니다")
    return unquote(name), role  # 헤더는 ASCII만 가능해 한글 이름은 URL 인코딩되어 옴


class TaskIn(BaseModel):
    tool: str = Field(min_length=1, max_length=20)
    run_id: str = Field(min_length=3, max_length=40)
    question: str = Field(min_length=2, max_length=1000)


class ApprovalIn(BaseModel):
    action: Literal["approve", "revise"]
    comment: str = Field("", max_length=1000)


@app.post("/api/ai/tasks", status_code=202)
def create_task(body: TaskIn, bg: BackgroundTasks, x_user_name: str = Header(None), x_user_role: str = Header(None)):
    name, role = user(x_user_name, x_user_role, {"worker", "engineer"})
    if not db.q("SELECT 1 FROM runs WHERE tool = %s AND run_id = %s", (body.tool, body.run_id)):
        raise HTTPException(404, f"{body.tool}에 run {body.run_id}가 없습니다")
    tid = str(uuid.uuid4())
    db.q("INSERT INTO tasks (id, user_name, user_role, question, tool, run_id, status) VALUES (%s,%s,%s,%s,%s,%s,'QUEUED')",
         (tid, name, role, body.question, body.tool, body.run_id))
    db.emit(tid, "QUEUED", {"by": name})
    # ponytail: 프로세스 내 백그라운드 실행. 재시작 시 진행 중 작업 유실 → Kafka 큐 + 재시도 단계에서 교체
    bg.add_task(graph.run, tid, {"task_id": tid, "question": body.question, "tool": body.tool, "run_id": body.run_id,
                                 "started_at": time.time(), "turns": 0})
    return {"taskId": tid}


@app.get("/api/ai/tasks")
def list_tasks(mine: bool = False, x_user_name: str = Header(None), x_user_role: str = Header(None)):
    name, role = user(x_user_name, x_user_role)
    if mine or role == "worker":  # 작업자는 자기 요청만
        return db.q("SELECT id, user_name, question, tool, run_id, status, created_at, updated_at FROM tasks WHERE user_name = %s ORDER BY created_at DESC LIMIT 100", (name,))
    return db.q("SELECT id, user_name, user_role, question, tool, run_id, status, error, created_at, updated_at FROM tasks ORDER BY created_at DESC LIMIT 200")


@app.get("/api/ai/tasks/{tid}")
def get_task(tid: uuid.UUID, x_user_name: str = Header(None), x_user_role: str = Header(None)):
    name, role = user(x_user_name, x_user_role)
    rows = db.q("""SELECT t.*, i.id AS investigation_id, i.approved_by, i.approved_at
                   FROM tasks t LEFT JOIN investigations i ON i.task_id = t.id WHERE t.id = %s""", (tid,))
    if not rows or (role == "worker" and rows[0]["user_name"] != name):
        raise HTTPException(404, "작업이 없습니다")
    return rows[0]


@app.get("/api/ai/tasks/{tid}/stream")
async def stream(tid: uuid.UUID, request: Request, user_name: str = "", user_role: str = ""):
    # EventSource는 헤더를 못 보내므로 쿼리로 받음 (목업 인증)
    user(user_name, user_role)
    last = int(request.headers.get("last-event-id") or 0)

    async def gen():
        nonlocal last
        idle = 0
        while not await request.is_disconnected():
            # ponytail: 0.5초 폴링. Kafka 단계에서 consumer push 또는 LISTEN/NOTIFY로 교체
            rows = await asyncio.to_thread(db.q, "SELECT seq, type, payload, created_at FROM task_events WHERE task_id = %s AND seq > %s ORDER BY seq", (tid, last))
            for r in rows:
                last = r["seq"]
                data = json.dumps({**r["payload"], "at": r["created_at"].isoformat()}, ensure_ascii=False, default=str)
                yield f"id: {r['seq']}\nevent: {r['type']}\ndata: {data}\n\n"
                if r["type"] in ("DONE", "FAILED"):
                    return
            idle = 0 if rows else idle + 1
            if idle and idle % 30 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/ai/tasks/{tid}/approval", status_code=202)
def approval(tid: uuid.UUID, body: ApprovalIn, bg: BackgroundTasks, x_user_name: str = Header(None), x_user_role: str = Header(None)):
    name, _ = user(x_user_name, x_user_role, {"engineer"})
    # 상태 전이를 조건부 UPDATE 하나로 → 중복 승인 차단
    if not db.q("UPDATE tasks SET status = 'RUNNING', updated_at = now() WHERE id = %s AND status = 'WAITING_APPROVAL' RETURNING id", (tid,)):
        raise HTTPException(409, "승인 대기 중인 작업이 아닙니다")
    db.emit(str(tid), "REVIEWED", {"by": name, "action": body.action, "comment": body.comment})
    bg.add_task(graph.run, str(tid), Command(resume={"action": body.action, "comment": body.comment, "by": name}))
    return {"taskId": str(tid)}


# ---- 화면 보조 API (Spring Boot 단계에서 업무 API /api/**로 이관) ----
@app.get("/api/runs")
def runs(tool: str = "01M01", q: str = "", x_user_name: str = Header(None), x_user_role: str = Header(None)):
    user(x_user_name, x_user_role)
    return db.q("""SELECT run_id, lot, stage, recipe, round(((end_time - start_time) / 60)::numeric, 1)::float8 AS minutes
                   FROM runs WHERE tool = %s AND run_id LIKE %s ORDER BY end_time DESC LIMIT 20""", (tool, f"%{q}%"))


@app.get("/api/runs/near-faults")
def near_faults(x_user_name: str = Header(None), x_user_role: str = Header(None)):
    """시연용: 고장 기록 직전 run. 작업자가 '이상해 보이는 run'으로 고르는 예시"""
    user(x_user_name, x_user_role)
    return db.q("""SELECT f.tool, r.run_id, r.recipe, f.fault_name, round(((f.time - r.end_time) / 3600)::numeric, 2)::float8 AS hours_before
                   FROM faults f JOIN LATERAL (SELECT * FROM runs WHERE tool = f.tool AND end_time <= f.time
                                               ORDER BY end_time DESC LIMIT 1) r ON true ORDER BY f.time""")


@app.get("/api/admin/overview")
def overview(x_user_name: str = Header(None), x_user_role: str = Header(None)):
    user(x_user_name, x_user_role, {"admin"})
    return {
        "status": db.q("SELECT status, count(*)::int AS n FROM tasks GROUP BY status"),
        "investigations": db.q("SELECT id, tool, run_id, approved_by, approved_at, report->>'summary' AS summary FROM investigations ORDER BY approved_at DESC LIMIT 50"),
        "docs": db.q("SELECT source, count(*)::int AS chunks, max(embed_model) AS embed_model FROM doc_chunks GROUP BY source ORDER BY source"),
        "data": db.q("SELECT tool, count(*)::int AS runs, (SELECT count(*)::int FROM faults f WHERE f.tool = r.tool) AS faults FROM runs r GROUP BY tool"),
        "tool_calls": db.q("""SELECT payload->>'name' AS name, count(*)::int AS calls,
                                     round(avg((payload->>'ms')::int))::int AS avg_ms,
                                     count(*) FILTER (WHERE payload->>'ok' = 'false')::int AS errors
                              FROM task_events WHERE type = 'TOOL_END' GROUP BY 1 ORDER BY 2 DESC"""),
    }
