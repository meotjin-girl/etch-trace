# Frontend (Vue 3 + TypeScript)

`frontend/`의 정적 화면(index.html, app.js, api.js, sop.js, markdown.js, sop-data.js)을 Vite + Vue 3 SFC + TypeScript, Pinia, Vue Router로 옮긴다. 화면·동작·`/api` 계약은 그대로이고 구조만 바뀐다. 시각 계약은 `frontend/DESIGN.md`를 따른다.

> 이 문서는 `feature/frontend` 작업용이다. `docs/architecture.md`, `AGENTS.md`, `README.md`는 다른 작업과 합칠 때 함께 갱신한다.

## 구조

| 위치 | 책임 | 이전 |
|---|---|---|
| `src/api/client.ts` | `/api/ai/tasks` REST·SSE 호출, 목업 신원(`X-User-Name`, `X-User-Role`, SSE 쿼리), `mergeEvents` | `api.js` |
| `src/api/types.ts` | `Task`, `TaskEvent`, `Report`, `Metric`, `CauseCase`, `Document`, `Review`, `Role` | — |
| `src/api/sop.ts` | SOP 샘플 `listSops()`, `getSop(id)`. 백엔드 SOP API로 교체할 경계 | `sop-data.js` |
| `src/lib/markdown.ts` | 표시 전용 마크다운 렌더러(원시 HTML 이스케이프, 링크 http/https/mailto 제한). SOP 본문과 보고서 본문에 공통 사용, 보고서의 `[SOP-ID §절]` 인용을 인용 버튼으로 변환 | `markdown.js` |
| `src/lib/format.ts` | 상태 라벨, 날짜 포맷, 진행 단계 계산 | `app.js` 상단 |
| `src/stores/identity.ts` | 이름·역할, 역할별 `api` 인스턴스. 변경 시 조사·기록 초기화 | `changeIdentity` |
| `src/stores/investigation.ts` | 현재 조사, 이벤트·`after` 커서, SSE 연결, `epoch`/`syncVersion` 가드, 질문·추가 정보·검토 제출 | `app.js` state |
| `src/stores/records.ts` | 서버 기록 목록·상세, 로컬 읽기 전용 기록(`etch-investigation-records-v1`) | `refreshRecords`, `selectRecord` |
| `src/stores/ui.ts` | 근거 패널 열림·하이라이트, SOP 검색어, 네트워크 알림 | DOM 토글 |
| `src/router/` | history 모드. `/` 이상 조사, `/records/:id?` 조사 기록, `/sop/:id?` SOP 목록 | `setPage()` |
| `src/views/`, `src/components/` | 기존 마크업·클래스를 유지한 SFC | `index.html` |
| `src/assets/styles.css` | 기존 전역 스타일 그대로 | `styles.css` |

## 규칙

- 아이콘은 Flaticon UIcons(`@flaticon/flaticon-uicons`, regular rounded, `fi-rr-*` 클래스)를 쓴다. 무료 라이선스 조건인 출처 표기("Uicons by Flaticon")를 사이드바 하단에 유지한다.
- backend·사용자·로컬 기록 값은 Vue 보간으로만 출력한다. `v-html`은 `renderMarkdown` 결과에만 쓴다.
- 상태는 backend detail이 기준이고, 이벤트 replay는 진행 표시와 이력만 만든다. 늦게 도착한 응답·콜백은 `epoch`/`syncVersion`으로 버린다.
- `/messages`는 소유자 + `WAITING_INPUT`, 검토는 engineer + `WAITING_APPROVAL`일 때만 UI에서 허용한다. 최종 권한 검사는 backend가 한다.
- 로컬 기록은 읽기 전용이며 승인으로 취급하지 않는다.

## 필요 API

프론트가 호출하는 전체 목록이다. 1~7은 현재 backend(`docs/api.md`)에 있고, 8·9는 신규 요청이다. 대화형 흐름에 필요한 이벤트 변경은 아래 "대화형 계약 제안"에 있다.

| # | 메서드·경로 | 화면에서의 용도 | 상태 |
|---|---|---|---|
| 1 | `GET /api/ai/tasks` | 기록 목록, 사이드바 건수 | 구현됨 |
| 2 | `POST /api/ai/tasks` | 새 질문 | 구현됨 |
| 3 | `GET /api/ai/tasks/{id}` | 조사 열기, 기록 상세, 동기화 | 구현됨 |
| 4 | `POST /api/ai/tasks/{id}/messages` | 재질문 답변(빠른 답변 버튼 포함) | 구현됨 |
| 5 | `POST /api/ai/tasks/{id}/approval` | 채팅의 [승인] [미승인], 판별 대기 중 입력한 수정 요청 | 구현됨 (+agent 동작 변경 제안) |
| 6 | `GET /api/ai/tasks/{id}/events?after=` | 다시 연결 | 구현됨 |
| 7 | `GET /api/ai/tasks/{id}/stream` (SSE) | 진행 표시, 토큰 스트리밍 | 구현됨 (+제안 이벤트) |
| 8 | `GET /api/sops` | SOP 목록 | **신규 요청** |
| 9 | `GET /api/sops/{id}` | SOP 상세 | **신규 요청** |
| — | `GET /api/me` | 사이드바 사용자 | 후속(로그인). 지금은 `identity` 스토어 기본값 |

공통 헤더는 `X-User-Name: %EC%9D%B4%EC%97%94%EC%A7%80%EB%8B%88%EC%96%B4`(URL 인코딩한 이름)와 `X-User-Role: engineer`다. SSE만 같은 값을 `user_name`, `user_role` 쿼리로 보낸다. 오류는 `{"detail":"..."}`이며 401(신원 없음), 403(역할 위반), 404(볼 수 없는 작업), 409(상태 불일치), 422(본문·커서 검증 실패)다.

### 예시

**1. `GET /api/ai/tasks`** → 200
```json
[{"id":"6f1c…","user_name":"이엔지니어","user_role":"engineer","question":"ETCH-07 CH-B OX-120 endpoint 118초 지연",
  "status":"WAITING_APPROVAL","report":{…},"created_at":"2026-10-20T01:00:00Z","updated_at":"2026-10-20T01:02:10Z"}]
```

**2. `POST /api/ai/tasks`** `{"question":"ETCH-07 CH-B OX-120 endpoint 118초 지연, RF reflected 29W"}` → 202 `{"taskId":"6f1c…"}`

**3. `GET /api/ai/tasks/{id}`** → 200: 1번 필드에 아래가 추가된다.
```json
{"messages":[{"role":"user","text":"ETCH-07 …","created_at":"…"},{"role":"assistant","text":"어느 장비와 챔버에서 발생했나요?","created_at":"…"}],
 "events":[{"seq":1,"type":"QUEUED","payload":{"by":"이엔지니어"},"created_at":"…"}],
 "reviews":[{"action":"revise","comment":"RF 근거 보강","by":"이엔지니어","role":"engineer","created_at":"…"}],
 "investigation":null}
```
report (RAG 마크다운 보고서, 아래 "보고서 형식" 참고):
```json
{"markdown":"## 요약\nETCH-07 CH-B OX-120에서 endpoint 지연이 관찰되었습니다. [SOP-ETCH-12 §3] 순서에 따라 측정 조건부터 확인합니다.\n\n## 점검 순서\n1. 측정 시점·조건 확인 [SOP-ETCH-12 §3]\n2. 반사전력 변화와 공정 변화 비교 [SOP-RF-03 §3]",
 "sources":[{"id":"SOP-ETCH-12","section":"3","heading":"3. 조사 순서","title":"식각 공정 이상 대응 절차","excerpt":"현재 관찰된 사실과 측정 조건을 확인합니다. …"},
            {"id":"SOP-RF-03","section":"3","heading":"3. 확인할 근거","title":"RF 반사전력 이상 조사 가이드","excerpt":"계측 이력: 반사전력 변화와 동시 발생한 공정 변화 …"}],
 "context":{"equipment":"ETCH-07","chamber":"CH-B","recipe":"OX-120"},
 "feedback":[],"demo":true}
```
화면은 `events`의 순서로 채팅을 그린다: `QUEUED`(첫 질문), `MESSAGE`(사용자 답변), `QUESTION`(재질문), `APPROVAL_REQUIRED`(보고서), `REVIEWED`(승인/미승인), `DONE`·`FAILED`·`INCOMPLETE`.

**4. `POST /api/ai/tasks/{id}/messages`** `{"text":"ETCH-07 CH-B"}` → 202 `{"taskId":"6f1c…"}`

**5. `POST /api/ai/tasks/{id}/approval`** → 202 `{"taskId":"6f1c…"}`
```json
{"action":"approve"}
{"action":"revise","comment":""}
{"action":"revise","comment":"RF 관련 근거를 다시 확인해 주세요"}
```
[승인]은 첫째, [미승인]은 둘째, 판별 대기 중 입력창에 쓴 글은 셋째 형태로 보낸다.

**6. `GET /api/ai/tasks/{id}/events?after=3`** → 200 `[{"seq":4,"type":"SEARCH_STARTED","payload":{},"created_at":"…"}]`

**7. `GET /api/ai/tasks/{id}/stream?user_name=…&user_role=engineer&after=3`** (`text/event-stream`)
```
id: 4
event: SEARCH_STARTED
data: {"seq":4,"type":"SEARCH_STARTED","payload":{},"created_at":"…"}

event: TOKEN
data: {"delta":"## 요약\nETCH-07 CH-B","target":"report"}

id: 7
event: APPROVAL_REQUIRED
data: {"seq":7,"type":"APPROVAL_REQUIRED","payload":{"report":{…},"text":"보고서를 판별해 주세요","options":["승인","미승인"]},"created_at":"…"}

: keep-alive
```

**8. `GET /api/sops`** → 200
```json
[{"id":"SOP-ETCH-12","title":"식각 공정 이상 대응 절차","category":"공정 이상 대응","version":"1.2",
  "updatedAt":"2026-10-12","owner":"공정기술팀","description":"…","tags":["식각","Endpoint"],"demo":true}]
```

**9. `GET /api/sops/{id}`** → 200: 8번 항목 하나에 `"markdown":"## 1. 목적\n…"`이 추가된다. 없으면 404 `{"detail":"문서를 찾을 수 없습니다."}`.

**후속 `GET /api/me`** → 200 `{"name":"이엔지니어","role":"engineer"}`

## 대화형 계약 제안 (agent·backend 구현 요청)

이해관계자는 엔지니어 한 명이다. 같은 엔지니어가 질문하고, 보고서를 받아 판별한다. 에이전트는 부족한 데이터를 계속 재질문하고, 승인·미승인 결과도 다시 에이전트로 돌아가 다음 질문이 이어진다(Gradio식 채팅). 엔드포인트는 그대로이고 이벤트 payload와 agent의 다음 행동만 바뀐다. 아래 필드가 없는 현재 backend에서도 화면은 동작한다(판별 버튼 기본값 `["승인","미승인"]`).

1. **`QUESTION {text, missing?, options?}`**: 필요할 때마다 재질문한다(현재 3회 제한은 agent 정책으로 조정). `options`는 빠른 답변 버튼이며 누르면 `/messages {text: option}`으로 간다.
   ```json
   {"type":"QUESTION","payload":{"text":"어느 장비와 챔버에서 발생했나요?","missing":["scope"],"options":["ETCH-07 CH-B","ETCH-09 CH-A"]}}
   ```
2. **`APPROVAL_REQUIRED {report, text?, options?}`**: 채팅에 판별 버튼을 띄운다. `/approval`은 지금처럼 engineer + `WAITING_APPROVAL`만 허용한다.
3. **판별 이후 agent 동작**
   - `revise` + 빈 comment → `QUESTION {"text":"어떤 부분을 수정할까요?"}` → 답변 → 재작성 → `APPROVAL_REQUIRED`
   - `revise` + comment → 바로 재작성 → `APPROVAL_REQUIRED`(현재 동작)
   - `approve` → `QUESTION {"text":"기록할 발생 시각과 Lot ID를 알려주세요","options":["건너뛰기"]}` → 답변 → `DONE {"report":…,"approved":true,"by":"이엔지니어"}`. 답에서 얻은 `event_time`·`lot_id`를 승인 스냅샷에 반영한다(파싱 주체는 팀 결정). 승인 뒤 잠시 `WAITING_INPUT`이 되며 DONE 시점이 늦어진다.
4. **`TOKEN {delta, target}`**: 저장하지 않는 SSE 전용 이벤트다. `id` 없이 보내고 replay 대상이 아니다. `target`은 `"message"`(재질문 문장) 또는 `"report"`(보고서 마크다운 본문). 화면은 흘러온 마크다운을 그때그때 렌더링한다. 뒤따르는 저장 이벤트가 최종본이므로 TOKEN이 유실돼도 데이터는 잃지 않는다.
5. **보고서 형식 (RAG 마크다운, 수치 카드 폐지)**: 보고서는 SOP 같은 .md 문서를 RAG로 검색해 만든 마크다운 본문과 출처 목록이다. 기존 `metrics`, `causeCases`, `docIds`, `documents`, `summary`, `scored`, `unknowns`는 쓰지 않는다.

   | 필드 | 타입 | 설명 |
   |---|---|---|
   | `markdown` | string, 필수 | 보고서 본문. 제목(`##`), 문단, 순서·비순서 목록, 표, 인용(`>`), 굵게·기울임, 코드, 링크만 사용한다. 원시 HTML·이미지·중첩 목록은 표시되지 않는다 |
   | `sources` | `{id, section, heading, title, excerpt}[]` | RAG가 근거로 쓴 SOP 조각. `id`는 SOP 문서 ID(`/api/sops/{id}`와 같음), `section`은 절 번호(`"3"`, `"3.2"`), `heading`은 그 절의 제목, `excerpt`는 인용한 원문 일부 |
   | `context` | `{equipment?, chamber?, recipe?}` | 선택. 채팅·기록 제목에 쓴다 |
   | `feedback` | string[] | 반영한 미승인 수정 요청 |
   | `demo` | boolean | 샘플 근거 여부. `true`면 "데모 데이터"로 표시한다 |

   **인용 형식 `[SOP-ID §절]`**: 본문에서 근거를 댈 때 `[SOP-ETCH-12 §3]`처럼 쓴다. SOP-ID는 `SOP-`로 시작하는 문서 ID, 절은 숫자와 점(`3`, `3.2`)이다. 한 문장에 여러 개면 `[SOP-ETCH-12 §3] [SOP-RF-03 §3]`처럼 나란히 쓴다. 화면은 이 표기를 인용 버튼으로 바꾸고, 누르면 오른쪽 근거 패널에서 같은 `id`·`section`의 출처를 강조한다. 출처 카드는 해당 SOP 화면(`/sop/{id}`)으로 연결된다. `sources`에 없는 인용은 버튼이 아닌 일반 글자로 남는다. 본문의 모든 인용은 `sources`에 대응 항목이 있어야 한다(agent 책임).

   **SOP 문서 규칙**: 절 번호로 인용하므로 SOP 마크다운의 절 제목은 `## 3. 조사 순서`처럼 번호로 시작해야 한다. 하위 절은 `### 3.2 …`. 현재 샘플 중 `SOP-RF-03`은 제목에 번호가 없어 구현 시 번호를 붙인다.
6. **역할**: 화면은 engineer만 쓴다. worker·admin 규칙은 backend에 남지만 화면에서 사용하지 않는다.

## 목업 서버

`npm run dev:mock`은 백엔드 없이 위 1~9와 대화형 제안을 메모리에서 흉내 낸다(`frontend/mock/`, dev 전용, 빌드 산출물에 포함되지 않음, 재시작하면 초기화).

| 입력 | 목업 동작 |
|---|---|
| 질문에 `ETCH-숫자`가 없음 | 장비·챔버 재질문(options) |
| 현상 키워드(endpoint, rf, 지연 등)가 없음 | 현상 재질문(options) |
| 정보 충분 | 진행 이벤트 → TOKEN(보고서 마크다운) → 판별 대기. 보고서는 SOP 샘플 문단을 인용한 마크다운 |
| [미승인] / 수정 요청 입력 | 수정 내용 재질문 / 바로 재작성 |
| [승인] | 발생 시각·Lot ID 재질문(건너뛰기) → DONE |
| 질문에 `실패` / `근거 없음` | FAILED / INCOMPLETE |

시드: 완료 1건, 판별 대기 1건, 장비 재질문 대기 1건(모두 이엔지니어).

## 실행

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, /api는 compose web(WEB_PORT)으로 프록시
npm run dev:mock     # 백엔드 없이 목업 API로 실행
npm run type-check
npm test             # Vitest
npm run build        # dist/
```

web 서비스는 `frontend/Dockerfile` 멀티스테이지(node 빌드 → nginx)로 만들 예정이며(미구현) `deploy/nginx.conf`로 `dist`를 서빙한다. 기존 `try_files ... /index.html`이 SPA 새로고침을 처리한다.

## 테스트

| 파일 | 범위 |
|---|---|
| `tests/api.spec.ts` | HTTP 계약·오류 구분·SSE 파싱/재연결 커서·이벤트 병합, SOP 경로, TOKEN 처리 |
| `tests/investigation.spec.ts` | 이벤트 순서 채팅, 빠른 답변·판별 버튼 대상, 채팅 판별 → `/approval`, TOKEN 스트리밍, 중복 전송 방지, 지연 콜백 차단, 최신 detail 우선 |
| `tests/render.spec.ts` | 보고서 이스케이프, 로컬 기록 읽기 전용, 마크다운 링크 제한, 라우트 스모크, 판별 버튼 렌더 |
| `tests/mock.spec.ts` | 목업 대화 흐름 전체, 권한·상태 오류, 종료 키워드, 시드 |
