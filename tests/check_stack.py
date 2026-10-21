"""Exercise the running v1 stack, including real MCP calls and checkpoints.

Run with PKCE-issued TRACE_ACCESS_TOKEN and TRACE_REVIEWER_TOKEN in the environment.
"""

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.getenv("TRACE_URL", "http://localhost:18080")
OWNER = os.getenv("TRACE_ACCESS_TOKEN", "")
REVIEWER = os.getenv("TRACE_REVIEWER_TOKEN", "")


def call(path, body=None, actor=OWNER, method=None):
    request = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {actor}",
        },
        method=method or ("POST" if body is not None else "GET"),
    )
    with urlopen(request, timeout=90) as response:
        return response.status, json.load(response)


def until(task_id, expected, after=0):
    """Subscribe to persisted SSE events; do not depend on timing sleeps."""
    path = f"/api/ai/tasks/{task_id}/stream?after={after}"
    event_type, sequence = "", after
    request = Request(BASE + path, headers={"Authorization": f"Bearer {OWNER}"})
    with urlopen(request, timeout=120) as response:
        for line in response:
            text = line.decode().rstrip("\r\n")
            if text.startswith("id: "):
                sequence = int(text[4:])
            elif text.startswith("event: "):
                event_type = text[7:]
            elif text.startswith("data: "):
                payload = json.loads(text[6:])
                if event_type == "FAILED":
                    raise AssertionError(payload)
                if event_type == expected:
                    return sequence, payload
    raise AssertionError(f"Stream ended before {expected}")


def denied(path, actor, body=None, status=403):
    try:
        call(path, body, actor)
    except HTTPError as error:
        assert error.code == status, (error.code, error.read())
    else:
        raise AssertionError(f"Expected HTTP {status}")


def main():
    if not OWNER or not REVIEWER:
        raise RuntimeError("Set TRACE_ACCESS_TOKEN and TRACE_REVIEWER_TOKEN from two PKCE logins")
    code, created = call("/api/ai/tasks", {"question": "비슷한 이상 사례를 찾아줘"})
    assert code == 202
    task_id = created["taskId"]
    path = f"/api/ai/tasks/{task_id}"
    seq, _ = until(task_id, "QUESTION")
    denied(path, "", status=401)
    denied(path + "/events", "", status=401)
    assert call(path, actor=REVIEWER)[0] == 200
    assert call(path + "/events", actor=REVIEWER)[0] == 200
    call(
        path + "/messages",
        {
            "text": "ETCH-07 CH-B OX-120 endpoint가 118초로 지연되고 RF reflected power가 29W로 상승했어",
        },
        REVIEWER,
    )
    seq, payload = until(task_id, "APPROVAL_REQUIRED", seq)
    report = payload["report"]
    assert report["demo"] is True
    assert report["context"]["metrics"]["endpoint_sec"] == 118
    assert report["scored"] and report["documents"]
    assert any(metric["key"] == "endpoint_sec" for metric in report["metrics"])
    reviewer = REVIEWER
    call(
        path + "/approval",
        {"action": "revise", "comment": "원인 확정 대신 점검 가설임을 유지"},
        reviewer,
    )
    seq, revised = until(task_id, "APPROVAL_REQUIRED", seq)
    assert revised["report"]["feedback"]
    call(
        path + "/approval",
        {
            "action": "approve",
            "event_time": "2026-10-20T10:00:00+09:00",
            "lot_id": "QA-LOT",
        },
        reviewer,
    )
    seq, _ = until(task_id, "DONE", seq)
    _, detail = call(path)
    assert detail["status"] == "DONE"
    assert detail["investigation"]["approved_by_id"] == detail["reviews"][-1]["user_id"]
    assert detail["investigation"]["approved_by_id"] != detail["user_id"]
    assert detail["investigation"]["lot_id"] == "QA-LOT"
    assert len(detail["reviews"]) == 2
    denied(path + "/approval", reviewer, {"action": "approve"}, status=409)
    _, replay = call(path + "/events")
    assert [event["seq"] for event in replay] == list(range(1, len(replay) + 1))
    _, records = call("/api/ai/tasks")
    assert task_id in [record["id"] for record in records]
    _, incomplete = call("/api/ai/tasks", {"question": "알려줘"})
    incomplete_id = incomplete["taskId"]
    cursor, _ = until(incomplete_id, "QUESTION")
    for attempt in range(3):
        call(f"/api/ai/tasks/{incomplete_id}/messages", {"text": "아직 몰라"})
        cursor, _ = until(
            incomplete_id,
            "INCOMPLETE" if attempt == 2 else "QUESTION",
            cursor,
        )
    print(
        f"PASS real stack: Bearer auth, shared clarification, MCP report, revise, approve, identity, replay, incomplete; task={task_id}"
    )


if __name__ == "__main__":
    main()
