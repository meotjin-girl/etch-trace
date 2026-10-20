# REST API 명세

🆕 = 오늘 추가되는 항목 (분류 기능). 나머지는 지금 서버에서 동작 중.

## 공통

| 항목 | 값 |
|---|---|
| Base URL | 서버 `http://32.236.188.208` · 로컬 `http://localhost:8000` |
| 형식 | JSON (UTF-8), 시각은 ISO 8601 |
| 인증 (목업) | 헤더 `X-User-Name`, `X-User-Role` — Supabase 도입 시 `Authorization: Bearer`로 교체 |
| 역할 | `worker` · `engineer` · `admin` |
| CORS 🆕 | 서버 `.env`의 `CORS_ORIGINS`(쉼표 구분)에 프론트 주소 등록 |

- 한글 이름은 헤더에 그대로 못 넣으므로 `encodeURIComponent(name)` 해서 보낸다.
- SSE(`EventSource`)는 헤더를 못 보내므로 쿼리 `?user_name=…&user_role=…` 로 보낸다.

### 오류

| 코드 | 의미 |
|---|---|
| 401 | 헤더 없음 / 잘못된 역할 |
| 403 | 역할 권한 없음 (예: 작업자가 승인) |
| 404 | 없는 run / 작업, 또는 남의 작업 (작업자) |
| 409 | 승인 대기 상태가 아님 (중복 승인 등) |
| 422 | 요청 본문 검증 실패 |

응답 본문: `{ "detail": "메시지" }`

---

## 1. 조사 작업

### POST `/api/ai/tasks` — 조사 요청
권한: `worker`, `engineer`

```json
{ "tool": "01M01", "run_id": "10825571-1132", "question": "FlowCool 압력 알람 후 장비가 섰어요" }
```
| 필드 | 제약 |
|---|---|
| `tool` | 1–20자, 적재된 장비 |
| `run_id` | 3–40자, 해당 장비에 존재 (`GET /api/runs`로 조회) |
| `question` | 2–1000자. 증상을 자유롭게 — 분류에 쓰인다 |

응답 `202`
```json
{ "taskId": "6f1c…-uuid" }
```

### GET `/api/ai/tasks` — 목록
권한: 전체. `worker`는 항상 본인 것만. `?mine=true`면 누구든 본인 것만.

응답 `200` (최신순, 최대 200)
```json
[{ "id": "…", "user_name": "김작업", "user_role": "worker", "question": "…", "tool": "01M01",
   "run_id": "10825571-1132", "status": "WAITING_APPROVAL", "category": "EQUIPMENT", "error": null,
   "created_at": "…", "updated_at": "…" }]
```
`category` 🆕

### GET `/api/ai/tasks/{taskId}` — 상세
권한: 전체 (`worker`는 본인 것만)

응답 `200`
```json
{ "id": "…", "user_name": "…", "user_role": "…", "question": "…", "tool": "01M01", "run_id": "…",
  "status": "DONE", "category": "EQUIPMENT", "category_reason": "…",
  "report": { /* 아래 Report */ }, "error": null, "created_at": "…", "updated_at": "…",
  "investigation_id": 1, "approved_by": "이엔지", "approved_at": "…" }
```
`investigation_id` 등은 승인 저장 전이면 `null`. `category`, `category_reason` 🆕

### GET `/api/ai/tasks/{taskId}/stream` — 진행 이벤트 (SSE)
권한: 쿼리 `user_name`, `user_role`

```js
const es = new EventSource(`/api/ai/tasks/${id}/stream?user_name=${encodeURIComponent(name)}&user_role=${role}`)
es.addEventListener('TOOL_END', e => console.log(JSON.parse(e.data)))
es.addEventListener('DONE', () => es.close())
```
- 처음 연결하면 지난 이벤트부터 전부 재생된다. 끊긴 뒤 재연결하면 `Last-Event-ID`부터 이어서 받는다 (EventSource 자동).
- `DONE`·`FAILED` 후 서버가 스트림을 닫는다. 30초마다 keep-alive 주석이 온다.

### POST `/api/ai/tasks/{taskId}/approval` — 검토 결정
권한: `engineer`. 상태가 `WAITING_APPROVAL`일 때만 (아니면 409).

```json
{ "action": "approve" }
{ "action": "revise", "comment": "z < 3 항목은 '경미한 편차'로 표현" }
{ "action": "revise", "comment": "공정 쪽으로 다시 봐주세요", "category": "PROCESS" }
```
| 필드 | 값 |
|---|---|
| `action` | `approve` 저장 / `revise` 재작성 |
| `comment` | 0–1000자 |
| `category` 🆕 | 선택. `EQUIPMENT` · `PROCESS` · `UNCLEAR` — 주면 그 분기로 다시 조사 |

응답 `202` `{ "taskId": "…" }` — 결과는 SSE로 온다 (`REVIEWED` → … → `APPROVAL_REQUIRED` 또는 `DONE`).

---

## 2. SSE 이벤트

각 이벤트: `id: <seq>`, `event: <TYPE>`, `data: <JSON>` (모든 data에 `at` 시각 포함)

| TYPE | 언제 | data |
|---|---|---|
| `QUEUED` | 생성 | `{ by }` |
| `CLASSIFIED` 🆕 | 분류·재분류 | `{ category, confidence, reason, reroute }` — `reroute: true`면 재분류 |
| `PLAN` | 매 턴 | `{ turn, reason, next, branch🆕 }` — `next`는 다음 도구명 또는 `null`(종료) |
| `TOOL_START` | 도구 시작 | `{ name, args }` |
| `TOOL_END` | 도구 끝 | `{ name, ms, ok, result }` |
| `TOKEN` | 보고서 작성 | `{ text }` (요약문) |
| `APPROVAL_REQUIRED` | 승인 대기 | `{ report, revision }` — `revision`은 수정 요청 반영 횟수 |
| `REVIEWED` | 엔지니어 결정 | `{ by, action, comment, category🆕 }` |
| `DONE` | 종료 | `{ saved: { saved, investigation_id \| reason }, report }` |
| `FAILED` | 오류 | `{ error }` |

### 작업 상태 `status`
`QUEUED` → `RUNNING` → `WAITING_APPROVAL` ⇄ `RUNNING` → `DONE` (오류 시 `FAILED`)

### Report

```json
{
  "category": "EQUIPMENT",
  "category_reason": "…",
  "summary": "한두 문장 요약 (원인 단정 없음)",
  "facts": ["도구 결과에서 나온 사실"],
  "evidence": ["문서명 > 섹션"],
  "next_actions": ["엔지니어가 확인할 것"],
  "unknowns": ["데이터로 알 수 없는 것"]
}
```
`category`, `category_reason` 🆕

---

## 3. 화면 보조

### GET `/api/runs?tool=01M01&q=1132` — run 검색
권한: 전체. 최신순 20개.
```json
[{ "run_id": "10825571-1132", "lot": "1132", "stage": "…", "recipe": "…", "minutes": 12.4 }]
```

### GET `/api/runs/near-faults` — 고장 직전 run (시연용 예시)
권한: 전체
```json
[{ "tool": "01M01", "run_id": "…", "recipe": "…", "fault_name": "Flowcool leak", "hours_before": 2.1 }]
```

### GET `/api/admin/overview` — 관리자 대시보드
권한: `admin`
```json
{
  "status": [{ "status": "DONE", "n": 3 }],
  "category": [{ "category": "EQUIPMENT", "n": 2 }],
  "investigations": [{ "id": 1, "tool": "…", "run_id": "…", "approved_by": "…", "approved_at": "…", "summary": "…" }],
  "docs": [{ "source": "investigation_guide.md", "chunks": 6, "embed_model": "text-embedding-3-small" }],
  "data": [{ "tool": "01M01", "runs": 11475, "faults": 19 }],
  "tool_calls": [{ "name": "compare_signals", "calls": 5, "avg_ms": 120, "errors": 0 }]
}
```
`category` 🆕

## 빠른 확인 (curl)

```bash
curl -s -X POST http://32.236.188.208/api/ai/tasks \
  -H 'Content-Type: application/json' -H 'X-User-Name: kim' -H 'X-User-Role: worker' \
  -d '{"tool":"01M01","run_id":"10825571-1132","question":"FlowCool 압력 알람 후 정지"}'
curl -N "http://32.236.188.208/api/ai/tasks/<taskId>/stream?user_name=lee&user_role=engineer"
```
