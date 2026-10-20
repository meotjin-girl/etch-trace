# Frontend (Vue 3 + TypeScript)

`frontend/`의 정적 화면(index.html, app.js, api.js, sop.js, markdown.js, sop-data.js)을 Vite + Vue 3 SFC + TypeScript, Pinia, Vue Router로 옮긴다. 화면·동작·`/api` 계약은 그대로이고 구조만 바뀐다. 시각 계약은 `frontend/DESIGN.md`를 따른다.

> 이 문서는 `feature/frontend` 작업용이다. `docs/architecture.md`, `AGENTS.md`, `README.md`는 다른 작업과 합칠 때 함께 갱신한다.

## 구조

| 위치 | 책임 | 이전 |
|---|---|---|
| `src/api/client.ts` | `/api/ai/tasks` REST·SSE 호출, 목업 신원(`X-User-Name`, `X-User-Role`, SSE 쿼리), `mergeEvents` | `api.js` |
| `src/api/types.ts` | `Task`, `TaskEvent`, `Report`, `Metric`, `CauseCase`, `Document`, `Review`, `Role` | — |
| `src/api/sop.ts` | SOP 샘플 `listSops()`, `getSop(id)`. 백엔드 SOP API로 교체할 경계 | `sop-data.js` |
| `src/lib/markdown.ts` | 표시 전용 마크다운 렌더러(원시 HTML 이스케이프, 링크 http/https/mailto 제한) | `markdown.js` |
| `src/lib/format.ts` | 지표 라벨·단위, 상태 라벨, 날짜·숫자 포맷 | `app.js` 상단 |
| `src/stores/identity.ts` | 이름·역할, 역할별 `api` 인스턴스. 변경 시 조사·기록 초기화 | `changeIdentity` |
| `src/stores/investigation.ts` | 현재 조사, 이벤트·`after` 커서, SSE 연결, `epoch`/`syncVersion` 가드, 질문·추가 정보·검토 제출 | `app.js` state |
| `src/stores/records.ts` | 서버 기록 목록·상세, 로컬 읽기 전용 기록(`etch-investigation-records-v1`) | `refreshRecords`, `selectRecord` |
| `src/stores/ui.ts` | 근거 패널 열림·하이라이트, 검토 다이얼로그 대상, 네트워크 알림 | DOM 토글 |
| `src/router/` | history 모드. `/` 이상 조사, `/records/:id?` 조사 기록, `/sop/:id?` SOP 목록 | `setPage()` |
| `src/views/`, `src/components/` | 기존 마크업·클래스를 유지한 SFC | `index.html` |
| `src/assets/styles.css` | 기존 전역 스타일 그대로 | `styles.css` |

## 규칙

- backend·사용자·로컬 기록 값은 Vue 보간으로만 출력한다. `v-html`은 `renderMarkdown` 결과에만 쓴다.
- 상태는 backend detail이 기준이고, 이벤트 replay는 진행 표시와 이력만 만든다. 늦게 도착한 응답·콜백은 `epoch`/`syncVersion`으로 버린다.
- `/messages`는 소유자 + `WAITING_INPUT`, 검토는 engineer + `WAITING_APPROVAL`일 때만 UI에서 허용한다. 최종 권한 검사는 backend가 한다.
- 로컬 기록은 읽기 전용이며 승인으로 취급하지 않는다.

## 실행

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173, /api는 compose web(WEB_PORT)으로 프록시
npm run type-check
npm test             # Vitest
npm run build        # dist/
```

web 서비스는 `frontend/Dockerfile` 멀티스테이지(node 빌드 → nginx)로 만들고 `deploy/nginx.conf`로 `dist`를 서빙한다. 기존 `try_files ... /index.html`이 SPA 새로고침을 처리한다.

## 테스트

| 파일 | 범위 |
|---|---|
| `tests/api.spec.ts` | HTTP 계약·오류 구분·SSE 파싱/재연결 커서·이벤트 병합 |
| `tests/investigation.spec.ts` | 중복 전송 방지, 소유 대기 작업만 이어가기, 초기화 시 abort, 지연 콜백 차단, 최신 detail 우선, 수정 후 승인 replay, 검토 권한, 수정 요청 의견 필수 |
| `tests/render.spec.ts` | 보고서 이스케이프, 로컬 기록 읽기 전용, 마크다운 링크 제한 |
