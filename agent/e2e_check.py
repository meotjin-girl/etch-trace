"""서버 실행 중일 때: uv run python e2e_check.py
요청 → SSE로 APPROVAL_REQUIRED 까지 → 승인 전 저장 0건 확인 → 수정 요청 → 재승인 대기 → 승인 → DONE + 저장 1건."""
import json
import urllib.request

import db

BASE = "http://localhost:8000"


def call(method, path, body=None, name="kim", role="worker"):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-User-Name": name, "X-User-Role": role})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


def events_until(tid, stop, after=0):
    url = f"{BASE}/api/ai/tasks/{tid}/stream?user_name=lee&user_role=engineer"
    req = urllib.request.Request(url, headers={"Last-Event-ID": str(after)})
    seq, ev = after, None
    with urllib.request.urlopen(req, timeout=180) as r:
        for raw in r:
            line = raw.decode().rstrip("\n")
            if line.startswith("id: "):
                seq = int(line[4:])
            elif line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"  [{seq}] {ev}: {json.dumps(data, ensure_ascii=False)[:160]}")
                if ev in stop or ev == "FAILED":
                    return ev, data, seq


status, body = call("POST", "/api/ai/tasks", {"tool": "01M01", "run_id": "10825571-1132",
                    "question": "이 run 직후 FlowCool 압력 알람으로 장비가 섰어요. 같은 레시피 이전 run과 비교해서 조사해 주세요."})
assert status == 202
tid = body["taskId"]
ev, data, seq = events_until(tid, {"APPROVAL_REQUIRED"})
assert ev == "APPROVAL_REQUIRED", data
assert not db.q("SELECT 1 FROM investigations WHERE task_id = %s", (tid,)), "승인 전 저장 발생"

try:  # 작업자는 승인 불가
    call("POST", f"/api/ai/tasks/{tid}/approval", {"action": "approve"})
    raise AssertionError("worker approval allowed")
except urllib.error.HTTPError as e:
    assert e.code == 403

call("POST", f"/api/ai/tasks/{tid}/approval", {"action": "revise", "comment": "z-score가 3 미만인 항목은 '경미한 편차'로 표현해 주세요."}, "lee", "engineer")
ev, data, seq = events_until(tid, {"APPROVAL_REQUIRED"}, seq)
assert ev == "APPROVAL_REQUIRED" and data["revision"] == 1, data
call("POST", f"/api/ai/tasks/{tid}/approval", {"action": "approve"}, "lee", "engineer")
ev, data, seq = events_until(tid, {"DONE"}, seq)
assert ev == "DONE" and data["saved"]["saved"], data
assert len(db.q("SELECT 1 FROM investigations WHERE task_id = %s", (tid,))) == 1
print("e2e ok", tid, data["saved"]["investigation_id"])
