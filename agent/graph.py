"""TRACE 조사 그래프. 노드·분기는 설계 이미지와 1:1:
plan → tool_router → (도구 4종) → update_state → should_continue ─예→ plan
                                                               └아니오→ summarize → need_human_review ─예→ human_review → (수정) apply_feedback → summarize
                                                                                                 └아니오/승인→ finalize → END
Harness: 최대 8턴·120초·같은 도구 3회, 재시도 2회 + 대체 모델, 결과 길이 제한, 승인 전 저장 금지, 단계별 이벤트 기록."""
import json
import operator
import os
import time
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

import db
import tools

MAX_TURNS, MAX_SECONDS, MAX_SAME_TOOL, RESULT_CHARS = 8, 120, 3, 3000
PROMPTS = Path(__file__).with_name("prompts")


class State(TypedDict, total=False):
    task_id: str
    question: str
    tool: str
    run_id: str
    started_at: float
    next_call: dict | None  # {"name", "args", "reason"}
    last_result: dict | None
    evidence: Annotated[list, operator.add]  # [{"name", "args", "result", "ok"}]
    turns: int
    report: dict
    feedback: Annotated[list, operator.add]
    approval: dict
    saved: dict


class Report(BaseModel):
    summary: str
    facts: list[str]
    evidence: list[str]
    next_actions: list[str]
    unknowns: list[str]


def model(bind=None, structured=None):
    def make(name, retries):
        m = ChatOpenAI(model=name, max_retries=retries, timeout=60)
        if bind:
            m = m.bind_tools(bind)
        if structured:
            m = m.with_structured_output(structured)
        return m
    return make(os.getenv("OPENAI_MODEL", "gpt-5.4-mini"), 2).with_fallbacks(
        [make(os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4.1-mini"), 1)])


def _dump(x, limit=RESULT_CHARS):
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…(잘림)"


def _ok(name, s):
    return [e for e in s.get("evidence", []) if e["name"] == name and e["ok"]]


def _fallback_plan(s):
    # Recovery: LLM 사용 불가 시 고정 순서. 이미 성공한 도구는 건너뜀
    tool, run_id = s["tool"], s["run_id"]
    if not _ok("get_run_context", s):
        return {"name": "get_run_context", "args": {"tool": tool, "run_id": run_id}}
    if not _ok("find_reference_runs", s):
        return {"name": "find_reference_runs", "args": {"tool": tool, "run_id": run_id}}
    refs = _ok("find_reference_runs", s)
    if refs and not _ok("compare_signals", s):
        ids = refs[-1]["result"]["reference_run_ids"]
        return {"name": "compare_signals", "args": {"tool": tool, "run_id": run_id, "reference_run_ids": ids}}
    if not _ok("search_knowledge", s):
        top = (_ok("compare_signals", s) or [{"result": {"top": [{}]}}])[-1]["result"]["top"][:1]
        sig = top[0].get("signal", "FLOWCOOLPRESSURE") if top else "FLOWCOOLPRESSURE"
        return {"name": "search_knowledge", "args": {"query": f"{sig} 편차 해석과 확인 순서"}}
    return None


# ---------- nodes ----------
def plan_node(s: State):
    history = "\n".join(f"- {e['name']}({_dump(e['args'], 300)}) → {_dump(e['result'], 1200)}" for e in s.get("evidence", []))
    msg = (f"조사 요청: {s['question']}\n대상: tool={s['tool']}, run_id={s['run_id']}\n"
           f"남은 턴: {MAX_TURNS - s.get('turns', 0)}\n지금까지의 도구 결과:\n{history or '(없음)'}")
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY 없음")
        ai = model(bind=list(tools.TOOLS.values())).invoke(
            [SystemMessage((PROMPTS / "plan.md").read_text()), HumanMessage(msg)])
        call = ai.tool_calls[0] if ai.tool_calls else None
        nxt = {"name": call["name"], "args": call["args"], "reason": ai.content or ""} if call else None
        reason = ai.content or (f"{call['name']} 호출" if call else "조사 종료")
    except Exception as e:
        nxt = _fallback_plan(s)
        reason = f"[폴백: {type(e).__name__}] 고정 순서로 진행"
    db.emit(s["task_id"], "PLAN", {"turn": s.get("turns", 0) + 1, "reason": reason, "next": nxt and nxt["name"]})
    return {"next_call": nxt}


def tool_router_node(s: State):
    call = s.get("next_call")
    if not call:
        return {"last_result": None}
    name, args = call["name"], dict(call.get("args") or {})
    if name not in tools.TOOLS:  # save_investigation 등 목록 밖 도구는 거부
        return {"last_result": {"name": name, "args": args, "result": {"error": f"허용되지 않은 도구 {name}"}}}
    if len([e for e in s.get("evidence", []) if e["name"] == name]) >= MAX_SAME_TOOL:
        return {"last_result": {"name": name, "args": args, "result": {"error": f"{name} 호출 한도({MAX_SAME_TOOL}회) 초과"}}}
    if name != "search_knowledge":
        args.setdefault("tool", s["tool"])
        args.setdefault("run_id", s["run_id"])
    db.emit(s["task_id"], "TOOL_START", {"name": name, "args": args})
    t0 = time.time()
    try:
        result = tools.TOOLS[name](**args)
    except Exception as e:  # 오류는 결과로 돌려줘 Agent가 다음 행동을 고르게 함
        result = {"error": f"{type(e).__name__}: {e}"}
    shown = result if len(_dump(result)) < RESULT_CHARS else {"preview": _dump(result, 800)}
    db.emit(s["task_id"], "TOOL_END", {"name": name, "ms": int((time.time() - t0) * 1000), "ok": "error" not in result, "result": shown})
    return {"last_result": {"name": name, "args": args, "result": result}}


def update_state_node(s: State):
    r = s.get("last_result")
    if not r:
        return {}
    ok = isinstance(r["result"], dict) and "error" not in r["result"]
    return {"evidence": [{**r, "ok": ok}], "turns": s.get("turns", 0) + 1, "last_result": None}


def should_continue(s: State):
    if not s.get("next_call"):
        return "summarize"
    if s.get("turns", 0) >= MAX_TURNS or time.time() - s["started_at"] > MAX_SECONDS:
        return "summarize"
    return "plan"


def _template_report(s):
    cmp = _ok("compare_signals", s)
    docs = _ok("search_knowledge", s)
    facts = [f"{d['step']} step {d['signal']}: z={d['z']} (대상 {d['target_mean']}, 참조 {d['ref_mean']}±{d['ref_std']}, n={d['n_ref']})"
             for d in (cmp[-1]["result"]["top"][:5] if cmp else [])]
    return Report(summary="원인 확정 불가. 참조 run 대비 편차가 큰 센서를 정리했습니다(LLM 미사용 템플릿).",
                  facts=facts or ["비교 결과 없음"],
                  evidence=[f"{d['source']} > {d['section']}" for d in (docs[-1]["result"].get("docs", []) if docs else [])],
                  next_actions=["편차 센서의 원 시계열 확인", "동일 기간 정비 이력 확인"],
                  unknowns=["센서값은 표준화되어 단위 없음", "고장 기록 시각은 정비 정지 시각"]).model_dump()


def summarize_node(s: State):
    ev = "\n".join(f"[{e['name']}] {_dump(e['result'])}" for e in s.get("evidence", []) if e["ok"])
    fb = "\n".join(f"- {f}" for f in s.get("feedback", []))
    msg = f"조사 요청: {s['question']}\n대상: {s['tool']} / {s['run_id']}\n도구 결과:\n{ev or '(없음)'}\n엔지니어 수정 요청:\n{fb or '(없음)'}"
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY 없음")
        report = model(structured=Report).invoke(
            [SystemMessage((PROMPTS / "summarize.md").read_text()), HumanMessage(msg)]).model_dump()
    except Exception:
        report = _template_report(s)
    db.emit(s["task_id"], "TOKEN", {"text": report["summary"]})
    return {"report": report}


def need_human_review(s: State):
    # 비교 결과가 있는 보고서만 검토·저장 대상. 근거가 없으면 미완료로 종료(저장 안 함)
    return "human_review" if _ok("compare_signals", s) else "finalize"


def human_review_node(s: State):
    decision = interrupt({"report": s["report"]})  # checkpointer에 상태 저장 후 정지 → 같은 thread_id로 재개
    return {"approval": decision}


def after_review(s: State):
    return "finalize" if s["approval"].get("action") == "approve" else "apply_feedback"


def apply_feedback_node(s: State):
    return {"feedback": [s["approval"].get("comment") or "표현을 더 신중하게 수정"]}


def finalize_node(s: State):
    if s.get("approval", {}).get("action") != "approve":
        return {"saved": {"saved": False, "reason": "근거 부족으로 미완료 종료 (승인 대상 아님)"}}
    return {"saved": tools.save_investigation(s["task_id"], s["tool"], s["run_id"], s["report"], s["approval"].get("by", "?"))}


g = StateGraph(State)
for name, fn in [("plan", plan_node), ("tool_router", tool_router_node), ("update_state", update_state_node),
                 ("summarize", summarize_node), ("human_review", human_review_node),
                 ("apply_feedback", apply_feedback_node), ("finalize", finalize_node)]:
    g.add_node(name, fn)
g.add_edge(START, "plan")
g.add_edge("plan", "tool_router")
g.add_edge("tool_router", "update_state")
g.add_conditional_edges("update_state", should_continue, ["plan", "summarize"])
g.add_conditional_edges("summarize", need_human_review, ["human_review", "finalize"])
g.add_conditional_edges("human_review", after_review, ["finalize", "apply_feedback"])
g.add_edge("apply_feedback", "summarize")
g.add_edge("finalize", END)

checkpointer = PostgresSaver(db.pool)
checkpointer.setup()
graph = g.compile(checkpointer=checkpointer)


def run(task_id, payload):
    """초기 State 또는 Command(resume=...)로 그래프를 실행하고 결과를 tasks/task_events에 기록."""
    config = {"configurable": {"thread_id": task_id}, "recursion_limit": 60}
    try:
        db.set_status(task_id, "RUNNING")
        graph.invoke(payload, config)
        st = graph.get_state(config)
        if st.next:  # human_review에서 interrupt
            db.set_status(task_id, "WAITING_APPROVAL", report=st.values["report"])
            db.emit(task_id, "APPROVAL_REQUIRED", {"report": st.values["report"], "revision": len(st.values.get("feedback", []))})
        else:
            v = st.values
            db.set_status(task_id, "DONE", report=v.get("report"))
            db.emit(task_id, "DONE", {"saved": v.get("saved"), "report": v.get("report")})
    except Exception as e:
        db.set_status(task_id, "FAILED", error=f"{type(e).__name__}: {e}")
        db.emit(task_id, "FAILED", {"error": f"{type(e).__name__}: {e}"})
