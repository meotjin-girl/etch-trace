# Frontend (Vue 3 + TypeScript)

`frontend/`는 Vite + Vue 3 SFC + TypeScript, Pinia, Vue Router 화면이다. 피그마 시안 기준 흐름은 이상 로그 → AI 조사(제안서·대화) → 원인 확인 → 조치 검토 → 조치 기록이며, 조사 기록과 SOP·OCAP 화면이 따로 있다. 시각 계약은 `frontend/DESIGN.md`를 따른다. 이전 질문 화면은 `/legacy`에 남아 있다(메뉴 없음).

> 서비스 전체 구조는 [architecture.md](architecture.md), 경로 지도는 [structure-review.md](structure-review.md)를 따른다.

## 구조

| 위치 | 책임 |
|---|---|
| `src/auth.ts`, `src/components/AuthGate.vue` | Keycloak PKCE·메모리 토큰·로그인 게이트 |
| `src/api/authenticated-http.ts` | Bearer 헤더·토큰 갱신·오류 구분을 공유하는 REST 클라이언트 |
| `src/api/live-investigations.ts`, `live-models.ts` | `/api/investigations` 목록·상세·승인·승인 취소·조치 기록과 응답 파서 |
| `src/api/agent-server.ts`, `agent-stream.ts`, `thread-messages.ts` | `/agent/threads/{id}` state·runs 조회, `runs/stream` values SSE, 화면에 보일 사용자·최종 답변 메시지 추출 |
| `src/api/client.ts`, `types.ts` | SOP API(`sops()`, `sop(id)`)와 레거시 `/api/ai/*` 작업·fetch SSE |
| `src/lib/alert-text.ts` | 경보 텍스트 파서(`docs/agent-request.md` 문법), rule·센서 한국어 이름, 상태(이상 탐지/조치 중/조치 완료) |
| `src/lib/markdown.ts` | 표시 전용 마크다운 렌더러(원시 HTML 이스케이프, 링크 http/https/mailto 제한). SOP 본문 표시 |
| `src/stores/identity.ts` | 검증된 로그인 상태·표시 이름·subject, 로그아웃 시 작업 상태 초기화 |
| `src/stores/live-investigations.ts` | 경보 조사 목록·상세·대화(진행 중 run 합류, 보낸 질문 즉시 표시)·승인·선택 취소·조치 기록, 목록 카드용 상세 미리보기 |
| `src/composables/useInvestigation.ts` | 한 조사의 단계 화면들이 열린 thread를 공유 |
| `src/stores/investigation.ts`, `records.ts`, `src/lib/format.ts` | 레거시 질문 화면·기록(로컬 읽기 전용 기록 포함) |
| `src/stores/ui.ts` | 근거 패널·검색어·네트워크 알림 |
| `src/router/` | `/` 이상 로그, `/investigations/:id` 조사 제안서, `…/candidates/:cid` 원인 후보 상세, `…/action` 조치 검토, `…/record` 조치 기록, `/records/:id?` 조사 기록, `/sop/:id?` SOP·OCAP, `/legacy`, `/legacy/records/:id?` |
| `src/views/`, `src/components/` | 시안 화면(`AppSidebar`, `PageHeader`(오른쪽 단계 표시 `StepBar`), `AlarmHeader`, `AiPanel`, `TraceIcon`)과 레거시 화면 SFC(`InvestigationView`, `RecordsView`, `ChatMessage`, `ReportView`, `EvidencePanel`, `RecordDetail`) |
| `src/assets/trace.css` | 디자인 토큰. `prefers-color-scheme`로 라이트·다크 자동 전환. 화면 전체는 고정 높이이고 필요한 영역만 내부 스크롤(1080px 이하는 일반 스크롤) |
| `src/assets/styles.css` | 레거시 화면 전역 스타일. 색은 `trace.css` 토큰 사용 |

## 규칙

- 아이콘은 Flaticon UIcons(`@flaticon/flaticon-uicons`, regular rounded, `fi-rr-*` 클래스)를 `TraceIcon`으로 쓴다. 무료 라이선스 조건인 출처 표기("Uicons by Flaticon")를 사이드바 하단에 유지한다.
- backend·사용자·경보 값은 Vue 보간으로만 출력한다. `v-html`은 `renderMarkdown` 결과에만 쓴다.
- 업무 상태(후보·승인·조치)는 backend detail이 기준이고, 대화는 Agent Server thread state가 기준이다. 둘은 독립적으로 다시 읽는다.
- 같은 thread에 진행 중 run이 있으면 새 run을 만들지 않고 합류한다(`multitask_strategy:"reject"`, 409 후 합류).
- 승인은 화면에 보인 `revision`과 후보 ID로 보낸다. 409면 자동 재시도하지 않고 최신 상세를 다시 읽는다.
- 조치 기록 전에는 원인 선택을 취소하고 다시 고를 수 있다. 조치 기록 후에는 바꿀 수 없다.
- 로그인 사용자는 소유자·역할 제한 없이 같은 조사를 읽고 대화·승인·기록한다. 최종 인증·상태 검사는 backend와 Agent Server가 한다.

## 호출 API

| 메서드·경로 | 화면에서의 용도 |
|---|---|
| `GET /api/auth/config` | Keycloak 초기화 |
| `GET /api/investigations` | 이상 로그·조사 기록 목록, 사이드바 건수 |
| `GET /api/investigations/{id}` | 제안서·후보·조치 화면, 목록 카드 미리보기 |
| `POST /api/investigations/{id}/approval` | 원인 선택 `{candidate_id, expected_revision, comment}` |
| `DELETE /api/investigations/{id}/approval` | 원인 다시 선택(조치 기록 전) |
| `POST /api/investigations/{id}/action` | 조치 기록 `{content, result}` |
| `GET /agent/threads/{id}/state` | 대화 복원 |
| `GET /agent/threads/{id}/runs` | 진행 중 run 확인 |
| `POST /agent/threads/{id}/runs/stream` | 후속 질문 `{"request":{"role":"user","content":…}}`, values SSE |
| `GET /agent/threads/{id}/runs/{run}/stream` | 진행 중 run 합류(values 스트림) |
| `GET /api/sops`, `/api/sops/{id}` | SOP·OCAP 목록·원문 |
| `/api/ai/*` | 레거시 `/legacy` 화면 전용 ([api.md](api.md#레거시-v1-작업-api)) |

요청·응답 필드는 [api.md](api.md)와 [agent-server.md](agent-server.md)를 따른다. 공통 헤더는 `Authorization: Bearer <access token>`이다. 토큰은 메모리에만 두며 요청 전 갱신한다. 로그아웃·갱신 실패·401은 조사·대화·스트림을 정리한다. `npm run dev:mock`만 개발 전용 목업 세션을 사용하며 프로덕션 빌드에서 인증을 우회하지 않는다.

## AI 대화 패널

`AiPanel`은 제안서·후보·조치 화면 오른쪽에 붙고 대화·센서 분석·문서 근거 탭이 있다. 센서 분석은 경보 텍스트의 센서 구간을 정상 평균 대비 편차(σ) 순으로, 문서 근거는 후보의 `doc_ids`를 SOP·OCAP 원문 링크로 보여 준다. 대화 탭에서 경보 thread의 첫 메시지(경보 원문)는 접어서 보여 주고, 보낸 질문은 서버 응답 전에 바로 말풍선으로 표시한다. 대화가 없으면 추천 질문(가장 유력한 원인은? 등)을 누르면 바로 보낸다. Enter로 보내고 Shift+Enter로 줄을 바꾼다. 실패하면 입력창 위에 오류를 표시한다. 도구 호출 중간 메시지는 화면에 보이지 않는다.

## 목업 서버

`npm run dev:mock`은 백엔드 없이 `/api`, `/agent`를 메모리에서 흉내 낸다(`frontend/mock/`, dev 전용, 빌드 산출물에 포함되지 않음, 재시작하면 초기화).

| 목업 | 동작 |
|---|---|
| `mock/live.ts` | 합성 경보 조사 4건 시드(이상 탐지 2, 조치 중 1, 조치 완료 1). 승인·선택 취소·조치 기록의 409 규칙, thread state, `runs/stream` 고정 답변 |
| `mock/store.ts`, `fixtures.ts` | 레거시 작업 흐름과 SOP 샘플 |

## 실행


```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, /api·/agent는 compose web(WEB_PORT)으로 프록시
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
| `tests/agent-server.spec.ts` | 업무 API Bearer·후보 검증, thread 메시지 추출, values SSE 분할 디코딩, 그래프 입력·합류 정책, 스트림 오류·취소 |
| `tests/live-investigations.spec.ts` | 승인 후 대화·사본 보존, 진행 중 run 합류, 409 후 합류, 승인 충돌 재조회, 중복 전송 방지, 로그아웃 중단 |
| `tests/live-render.spec.ts` | 이상 로그 → 제안서 → 후보 → 선택 → 재선택 → 조치 검토 → 조치 기록 → 조사 기록, 질문 즉시 표시, 추천 질문·오류 표시 |
| `tests/alert-text.spec.ts` | 경보 텍스트 파서, 상태 판정 |
| `tests/auth.spec.ts` | PKCE 초기화, 갱신 실패·로그아웃 정리 |
| `tests/api.spec.ts`, `investigation.spec.ts`, `render.spec.ts`, `mock.spec.ts` | 레거시 작업 API·SSE·채팅·보고서 렌더·목업과 마크다운 이스케이프, 라우트 스모크 |
