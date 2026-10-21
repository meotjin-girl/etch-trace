# Frontend (Vue 3 + TypeScript)

`frontend/`의 정적 화면(index.html, app.js, api.js, sop.js, markdown.js, sop-data.js)을 Vite + Vue 3 SFC + TypeScript, Pinia, Vue Router로 옮긴다. 화면·동작·`/api` 계약은 그대로이고 구조만 바뀐다. 시각 계약은 `frontend/DESIGN.md`를 따른다.

> 서비스 전체 구조는 [architecture.md](architecture.md), 경로 지도는 [structure-review.md](structure-review.md)를 따른다.

## 구조

| 위치 | 책임 | 이전 |
|---|---|---|
| `src/api/client.ts` | Bearer REST·fetch SSE, 토큰 갱신 후 커서 복원, `mergeEvents` | `api.js` |
| `src/auth.ts`, `src/components/AuthGate.vue` | Keycloak PKCE·메모리 토큰·로그인 게이트 | 인증 이식 |
| `src/api/types.ts` | `Task`, `TaskEvent`, `Report`, `Metric`, `CauseCase`, `Document`, `Review`, `Role` | — |
| `src/api/sop.ts` | SOP 샘플 `listSops()`, `getSop(id)`. 백엔드 SOP API로 교체할 경계 | `sop-data.js` |
| `src/lib/markdown.ts` | 표시 전용 마크다운 렌더러(원시 HTML 이스케이프, 링크 http/https/mailto 제한). SOP 본문 표시 | `markdown.js` |
| `src/lib/format.ts` | 상태·단계 라벨, 날짜 포맷, 사이드바 에이전트 흐름 계산(`agentFlow`) | `app.js` 상단 |
| `src/stores/identity.ts` | 검증된 로그인 상태·표시 이름·subject, 로그아웃 시 조사·기록·진행 요청 초기화 | `changeIdentity` |
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
- 로그인 사용자는 `WAITING_INPUT`에 답변하고 `WAITING_APPROVAL`을 검토할 수 있다. 소유자·역할 제한은 없고 로컬 기록은 수정할 수 없다. 최종 인증·상태 검사는 backend가 한다.
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
| 8 | `GET /api/sops` | SOP 목록 | backend 구현(`feature/backend-integration`, `sop-ocap/` 문서) |
| 9 | `GET /api/sops/{id}` | SOP 상세 | backend 구현(`feature/backend-integration`) |
| — | `GET /api/ai/investigations`, `/{id}` | (화면 미사용) 승인된 조사 이력 | backend가 직접 응답(`docs/structure-review.md` 2.2). nginx → business-mcp 직통은 제거 |
| — | `GET /api/auth/config` | Keycloak 초기화 | 구현됨. 사용자 표시는 어댑터 claims에서 가져오며 `/api/me`는 사용하지 않음 |

공통 헤더는 REST·SSE 모두 `Authorization: Bearer <access token>`이다. 토큰은 메모리에만 두며 요청 전 갱신한다. 로그아웃·갱신 실패·401은 조사·기록·SSE를 정리한다. 오류는 `{"detail":"..."}`이며 401(인증 실패), 404(자료 없음), 409(상태 불일치), 422(본문·커서 검증 실패), 503(JWKS 연결 장애)다. `npm run dev:mock`만 개발 전용 목업 세션을 사용하며 프로덕션 빌드에서 인증을 우회하지 않는다.

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
report (develop 계약 `docs/v1-contract.md`, 아래 "보고서 형식" 참고):
```json
{"context":{"equipment":"ETCH-07","chamber":"CH-B","recipe":"OX-120"},
 "summary":"관련 과거 사례 3건을 비교했습니다. …",
 "metrics":[{"key":"endpoint_sec","value":118,"severity":"high","mean":92.4,"deltaPct":27.7,"z":3.1}],
 "stages":[{"key":"scope","title":"범위 조사 에이전트","status":"sample_based","agent_mode":"rule_based",
            "findings":["…"],"unknowns":["MES Lot/Wafer 미연결"],"caseIds":["CASE-014"],"docIds":[],"historyIds":["…"]}],
 "history":[{"id":"…","question":"…","summary":"…","causes":["RF matching 열화"],"docIds":["DOC-RF-03"],
             "approvedBy":"이엔지니어","approvedAt":"…","eventTime":null,"lotId":"LOT-1"}],
 "causeCases":[{"id":"CASE-014","cause":"RF matching 열화","action":"매칭 네트워크 점검","docs":["DOC-RF-03"]}],
 "checks":[{"title":"SOP-ETCH-12 식각 장비 이상 대응 · 4 절차 / 4.2 Endpoint 지연 시 동시 비교","rationale":"…","source":"rag_mcp","docId":"SOP-ETCH-12#4.2"}],
 "docIds":["DOC-RF-03"],
 "documents":[{"id":"SOP-ETCH-12#4.2","title":"…","text":"…","is_demo":true,"source":"sop/…","revision":"…","notice":"…","distance":0.21}],
 "unknowns":["…"],"feedback":[],"demo":true}
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

**7. `GET /api/ai/tasks/{id}/stream?after=3`** (Bearer 헤더, `text/event-stream`)
```
id: 4
event: SEARCH_STARTED
data: {"seq":4,"type":"SEARCH_STARTED","payload":{},"created_at":"…"}

event: TOKEN
data: {"delta":"관련 과거 사례","target":"summary"}

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

**`GET /api/auth/config`** → 200 `{"url":"http://localhost:18080/auth","realm":"trace","clientId":"trace-web"}`. 사용자 이름·subject는 Keycloak 어댑터 claims로 표시한다.

## 대화형 계약 제안 (agent·backend 구현 요청)

이해관계자는 엔지니어 한 명이다. 같은 엔지니어가 질문하고, 보고서를 받아 판별한다. 에이전트는 부족한 데이터를 계속 재질문하고, 승인·미승인 결과도 다시 에이전트로 돌아가 다음 질문이 이어진다(Gradio식 채팅). 엔드포인트는 그대로이고 이벤트 payload와 agent의 다음 행동만 바뀐다. 아래 필드가 없는 현재 backend에서도 화면은 동작한다(판별 버튼 기본값 `["승인","미승인"]`).

1. **`QUESTION {text, missing?, options?}`**: 필요할 때마다 재질문한다(현재 3회 제한은 agent 정책으로 조정). `options`는 빠른 답변 버튼이며 누르면 `/messages {text: option}`으로 간다.
   ```json
   {"type":"QUESTION","payload":{"text":"어느 장비와 챔버에서 발생했나요?","missing":["scope"],"options":["ETCH-07 CH-B","ETCH-09 CH-A"]}}
   ```
2. **`APPROVAL_REQUIRED {report, text?, options?}`**: 채팅에 판별 버튼을 띄운다. `/approval`은 로그인 사용자 + `WAITING_APPROVAL`만 허용한다.
3. **판별 이후 agent 동작**
   - `revise` + 빈 comment → `QUESTION {"text":"어떤 부분을 수정할까요?"}` → 답변 → 재작성 → `APPROVAL_REQUIRED`
   - `revise` + comment → 바로 재작성 → `APPROVAL_REQUIRED`(현재 동작)
   - `approve` → `QUESTION {"text":"기록할 발생 시각과 Lot ID를 알려주세요","options":["건너뛰기"]}` → 답변 → `DONE {"report":…,"approved":true,"by":"이엔지니어"}`. 답에서 얻은 `event_time`·`lot_id`를 승인 스냅샷에 반영한다(파싱 주체는 팀 결정). 승인 뒤 잠시 `WAITING_INPUT`이 되며 DONE 시점이 늦어진다.
4. **`TOKEN {delta, target}`**: 저장하지 않는 SSE 전용 이벤트다. `id` 없이 보내고 replay 대상이 아니다. `target`은 `"message"`(재질문 문장) 또는 `"summary"`(보고서 요약). 뒤따르는 저장 이벤트가 최종본이므로 TOKEN이 유실돼도 데이터는 잃지 않는다.
5. **보고서 형식**: develop 계약(`docs/v1-contract.md`)을 그대로 따른다. 화면은 develop의 순서로 그린다: 요약 → 수치 카드(`metrics`) → 조사 단계별 결과(`stages`, 상태·LLM 사용 여부·미확인 항목) → 유사 승인 조사 이력(`history`) → 우선 확인할 항목(`causeCases`) → SOP RAG 검색 결과(`checks`, `docId` 인용) → 문서 근거(`docIds`). 인용 버튼은 같은 `id`의 `documents` 항목을 근거 패널에서 강조한다(SOP 조항 ID는 `SOP-ETCH-12#4.2` 형식).

   **사이드바 에이전트 흐름**: develop 그래프(`docs/agent.md`) 순서로 8단계를 표시한다 — 질문 접수, 범위 조사, 과거 Run 비교, 센서 교차 확인, 정비 이력 확인, 원인 후보·점검 추천, 보고서 구성, 엔지니어 판별. 진행은 저장 이벤트로만 판단한다(`SEARCH_STARTED` → 범위 조사, `ANALYSIS_STARTED` → 전문 에이전트 4단계 함께 진행 중, `REPORT_STARTED` → 보고서 구성, `APPROVAL_REQUIRED` → 판별). 센서·정비·추천 에이전트는 개별 이벤트가 없어 함께 표시하며, 보고서가 오면 `stages`의 상태로 단계별 결과를 보여 준다. 정확한 개별 진행을 원하면 agent가 `{key}`를 담은 단계 시작 이벤트를 추가하는 것을 제안한다.
6. **역할**: 로그인한 사용자는 동등하게 조회·답변·검토한다. 역할·소유자별 분리는 후속 범위다.

## 목업 서버

`npm run dev:mock`은 백엔드 없이 위 1~9와 대화형 제안을 메모리에서 흉내 낸다(`frontend/mock/`, dev 전용, 빌드 산출물에 포함되지 않음, 재시작하면 초기화).

| 입력 | 목업 동작 |
|---|---|
| 질문에 `ETCH-숫자`가 없음 | 장비·챔버 재질문(options) |
| 현상 키워드(endpoint, rf, 지연 등)가 없음 | 현상 재질문(options) |
| 정보 충분 | 진행 이벤트 → TOKEN(보고서 요약) → 판별 대기. 보고서는 develop 형식(stages 5개, RAG checks, 유사 승인 history 포함) |
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

web 서비스는 `frontend/Dockerfile` 멀티스테이지(node 빌드 → nginx)로 만들고 `deploy/nginx.conf`로 `dist`를 서빙한다. 기존 `try_files ... /index.html`이 SPA 새로고침을 처리한다.

실제 로그인으로 Vite dev 서버를 쓸 때는 `trace-web` 클라이언트의 Valid redirect URIs에
`http://localhost:5173/*`, Web origins에 `http://localhost:5173`을 별도로 추가한다.
기본 realm은 Compose의 공개 origin만 허용한다. backend issuer와 Keycloak URL은
Compose 공개 주소를 유지한다. `dev:mock`에는 이 설정이나 Keycloak이 필요하지 않다.

## 테스트

| 파일 | 범위 |
|---|---|
| `tests/api.spec.ts` | HTTP 계약·오류 구분·SSE 파싱/재연결 커서·이벤트 병합, SOP 경로, TOKEN 처리 |
| `tests/investigation.spec.ts` | 이벤트 순서 채팅, 빠른 답변·판별 버튼 대상, 채팅 판별 → `/approval`, TOKEN 스트리밍, 중복 전송 방지, 지연 콜백 차단, 최신 detail 우선 |
| `tests/render.spec.ts` | 보고서 이스케이프, 로컬 기록 읽기 전용, 마크다운 링크 제한, 라우트 스모크, 판별 버튼 렌더 |
| `tests/mock.spec.ts` | 목업 대화 흐름 전체, 권한·상태 오류, 종료 키워드, 시드 |
