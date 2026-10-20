"""조사 도구 5개. 입력/출력은 JSON 직렬화 가능한 dict → 다음 단계에서 그대로 @mcp.tool로 감싼다.
숫자는 여기서만 계산한다. LLM은 결과를 읽고 다음 행동만 고른다."""
import json
import os
import statistics

import db

EMBED_MODEL = "text-embedding-3-small"
# 누적 사용량 카운터는 시간이 지나면 당연히 커지므로 편차 비교에서 제외
COUNTERS = {"ETCHSOURCEUSAGE", "ETCHAUXSOURCETIMER", "ETCHAUX2SOURCETIMER"}


def _run(tool, run_id):
    rows = db.q("SELECT * FROM runs WHERE tool = %s AND run_id = %s", (tool, run_id))
    return rows[0] if rows else None


def get_run_context(tool: str, run_id: str) -> dict:
    """대상 run의 장비·recipe·stage·step 목록과, run 종료 시점 이전의 최근 고장 기록을 조회한다."""
    run = _run(tool, run_id)
    if not run:
        return {"error": f"{tool}의 run {run_id}가 없습니다. run_id는 '{{runnum}}-{{Lot}}' 형식입니다."}
    steps = db.q("""SELECT recipe_step, max(n) AS samples FROM run_steps
                    WHERE tool = %s AND run_id = %s GROUP BY recipe_step ORDER BY recipe_step""", (tool, run_id))
    # 미래 정보 누설 방지: run 종료 시점까지의 고장만
    faults = db.q("""SELECT fault_name, round(((%s - time) / 3600)::numeric, 1)::float8 AS hours_before_run_end
                     FROM faults WHERE tool = %s AND time <= %s ORDER BY time DESC LIMIT 3""",
                  (run["end_time"], tool, run["end_time"]))
    return {**{k: run[k] for k in ("tool", "run_id", "runnum", "lot", "stage", "recipe", "n_rows")},
            "duration_sec": run["end_time"] - run["start_time"], "steps": steps, "recent_faults": faults}


def find_reference_runs(tool: str, run_id: str, k: int = 8) -> dict:
    """같은 장비·같은 recipe의 이전 run 중, 고장 직전 24시간 구간에 걸리지 않은 run을 정상 비교 기준으로 고른다."""
    run = _run(tool, run_id)
    if not run:
        return {"error": f"run {run_id}가 없습니다."}
    k = max(3, min(int(k), 30))
    refs = db.q("""SELECT run_id, lot, stage FROM runs r
                   WHERE tool = %s AND recipe = %s AND end_time < %s
                     AND NOT EXISTS (SELECT 1 FROM faults f WHERE f.tool = r.tool AND f.time <= %s
                                     AND f.time BETWEEN r.end_time AND r.end_time + 86400)
                   ORDER BY end_time DESC LIMIT %s""",
                (tool, run["recipe"], run["start_time"], run["end_time"], k))
    if len(refs) < 3:
        return {"error": f"recipe {run['recipe']}의 비교 가능한 이전 run이 {len(refs)}건뿐입니다.", "references": refs}
    return {"criteria": f"tool={tool}, recipe={run['recipe']}, 대상 이전, 고장 직전 24h 제외, 최근 {k}건",
            "reference_run_ids": [r["run_id"] for r in refs], "references": refs}


def compare_signals(tool: str, run_id: str, reference_run_ids: list[str], top: int = 8) -> dict:
    """대상 run과 참조 run들의 step·센서별 평균을 비교해 z-score와 결측률 차이를 계산한다. |z| 큰 순으로 반환."""
    if not reference_run_ids:
        return {"error": "reference_run_ids가 비어 있습니다. find_reference_runs를 먼저 호출하세요."}
    rows = db.q("""SELECT run_id, recipe_step, signal, mean, missing_rate FROM run_steps
                   WHERE tool = %s AND run_id = ANY(%s)""", (tool, [run_id, *reference_run_ids]))
    target = {(r["recipe_step"], r["signal"]): r for r in rows if r["run_id"] == run_id}
    if not target:
        return {"error": f"run {run_id}의 센서 통계가 없습니다."}
    ref = {}
    for r in rows:
        if r["run_id"] != run_id and r["mean"] is not None:
            ref.setdefault((r["recipe_step"], r["signal"]), []).append(r)
    out = []
    for key, t in target.items():
        refs = ref.get(key, [])
        if key[1] in COUNTERS or len(refs) < 3 or t["mean"] is None:
            continue
        means = [r["mean"] for r in refs]
        mu, sd = statistics.fmean(means), statistics.stdev(means)
        z = (t["mean"] - mu) / sd if sd > 1e-9 else (0.0 if abs(t["mean"] - mu) < 1e-9 else float("inf"))
        out.append({"step": key[0], "signal": key[1], "target_mean": round(t["mean"], 4),
                    "ref_mean": round(mu, 4), "ref_std": round(sd, 4),
                    "z": round(z, 2) if z != float("inf") else "inf(참조값 일정)",
                    "missing_rate_diff": round(t["missing_rate"] - statistics.fmean(r["missing_rate"] for r in refs), 4),
                    "n_ref": len(refs)})
    out.sort(key=lambda d: -(abs(d["z"]) if isinstance(d["z"], float) else 1e9))
    return {"method": "z = (대상 평균 - 참조 평균들의 평균) / 참조 평균들의 표준편차. 값은 원본에서 표준화되어 단위 없음",
            "compared_pairs": len(out), "flagged_abs_z_ge_3": sum(1 for d in out if not isinstance(d["z"], float) or abs(d["z"]) >= 3),
            "top": out[:max(1, min(int(top), 20))], "excluded_counters": sorted(COUNTERS)}


def embed(texts: list[str]) -> list[list[float]]:
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBED_MODEL).embed_documents(texts)


def search_knowledge(query: str, k: int = 4) -> dict:
    """데이터 사전·장비 설명·조사 가이드에서 질문과 가까운 문서 조각을 찾아 출처와 함께 반환한다."""
    k = max(1, min(int(k), 8))
    if os.getenv("OPENAI_API_KEY"):
        vec = json.dumps(embed([query])[0])
        rows = db.q("""SELECT source, section, content, round((1 - (embedding <=> %s::vector))::numeric, 3)::float8 AS score
                       FROM doc_chunks WHERE embed_model = %s ORDER BY embedding <=> %s::vector LIMIT %s""",
                    (vec, EMBED_MODEL, vec, k))
    else:  # ponytail: 키 없을 때 키워드 폴백. 시연 안정성용
        rows = db.q("SELECT source, section, content, NULL AS score FROM doc_chunks WHERE content ILIKE %s LIMIT %s",
                    (f"%{query.split()[0]}%", k))
    if not rows:
        return {"found": False, "message": "관련 문서를 찾지 못했습니다. 근거 없음으로 기록하세요."}
    return {"found": True, "docs": [{**r, "content": r["content"][:600]} for r in rows]}


def save_investigation(task_id: str, tool: str, run_id: str, report: dict, approved_by: str) -> dict:
    """사람이 승인한 조사 보고서만 저장한다. 그래프의 finalize 노드에서만 호출되며 LLM 도구 목록에는 없다."""
    rows = db.q("""INSERT INTO investigations (task_id, tool, run_id, report, approved_by)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (task_id) DO NOTHING RETURNING id""",
                (task_id, tool, run_id, json.dumps(report, ensure_ascii=False), approved_by))
    return {"saved": bool(rows), "investigation_id": f"INV-{rows[0]['id']:04d}" if rows else None}


# LLM이 고를 수 있는 도구 (save_investigation 제외 — 승인 이후 코드에서만 호출)
TOOLS = {f.__name__: f for f in (get_run_context, find_reference_runs, compare_signals, search_knowledge)}


if __name__ == "__main__":
    # 셀프체크: 실데이터 01M01, 'FlowCool Pressure Dropped Below Limit' 14분 전 run
    ctx = get_run_context("01M01", "10825571-1132")
    assert ctx["recipe"] == "4" and ctx["steps"], ctx
    assert "error" in get_run_context("01M01", "nope")
    refs = find_reference_runs("01M01", "10825571-1132")
    assert len(refs["reference_run_ids"]) == 8 and "10825571-1132" not in refs["reference_run_ids"]
    cmp = compare_signals("01M01", "10825571-1132", refs["reference_run_ids"])
    assert cmp["compared_pairs"] > 0 and all(d["signal"] not in COUNTERS for d in cmp["top"])
    # 참조 run 하나를 대상으로 바꾸면 자기 자신은 참조에서 빠져야 함
    assert "error" in compare_signals("01M01", "10825571-1132", [])
    print(json.dumps(cmp["top"][:4], ensure_ascii=False, indent=1))
    print("tools ok")
