# Keycloak Vue 이식 검증 (2026-10-21)

기준은 `develop`의 `afad4cf`이며 작업 브랜치는 `feature/keycloak-vue-login`이다.
기존 PR #33의 `200d92e` 전체를 rebase/cherry-pick하지 않고 인증을 선별 이식했다.
Vue·최신 backend 이력/SOP API·Agent 요청자 전달·기존 nginx 경로를 보존했다.

## 단계별 결과

| 단계 | 실제 실행 결과 |
|---|---|
| Backend | `cd backend && uv run pytest -q`: 77 passed. 실제 PostgreSQL 격리 스키마·HTTP JWKS·서명 JWT 사용 |
| 내부 Agent | `cd agent && uv run pytest -q tests/test_main.py tests/test_mcp.py`: 10 passed |
| Vue | `cd frontend && npm test`: 48 passed. 인증·REST·fetch SSE·스토어·기존 화면·목업 포함 |
| 정적 검사 | 서비스별 basedpyright 0 errors/0 warnings, backend Ruff 통과, Vue type-check·production build 통과 |
| 배포 | 격리 Compose build/start/health 통과. nginx 설정 검사·Compose config·diff whitespace 통과 |

Backend 검증은 서명·알고리즘·issuer·audience·만료·subject·토큰 타입·키 선택 오류,
목업 신원/URL 토큰 거절, JWKS 장애, 공동 조회·답변·검토, 감사 ID,
새 이력·SOP API, SSE 만료 종료·커서 복원, 승인 경쟁·스냅샷·재시작을 포함한다.
새 사용자 역할 `user`는 실제 Agent HTTP 모델과 그래프 체크포인트까지 확인했다.

Vue 검증은 PKCE 초기화·익명 상태·갱신 실패·로그아웃·늦은 갱신/목록 응답 차단,
Bearer REST·401·취소·네트워크 오류, 분할 UTF-8/CRLF·여러 data 줄·불완전 EOF,
TOKEN/저장 이벤트 분리·잘못된 TOKEN 무시, 새 토큰과 마지막 seq로 재연결,
조기 EOF의 명시적 재시도, 이벤트 중복 제거를 포함한다.

## 실제 서비스와 브라우저

별도 프로젝트 `trace-keycloak-vue-qa`, 포트 `18280`, 새 DB·Keycloak 볼륨으로 실행했다.
기존 서비스와 `trace-rag-share`를 재시작하거나 볼륨을 공유하지 않았다.

- 실제 Keycloak Authorization Code + PKCE 로그인으로 서로 다른 두 계정을 인증했다.
- 실제 backend·Agent·Business/RAG MCP·PostgreSQL에서 재질문 → 다른 사용자 답변
  → 보고서 → 수정 → 승인 → DONE·승인 스냅샷 → 이력 조회를 검증했다.
- SSE replay, 중복 seq, 잘못된 상태의 검토 거절, 정보 부족 종료도 확인했다.
- 승인 이력 API와 SOP 22개 목록·상세가 Bearer 인증으로 동작하고 목업 헤더는 401이었다.
- 실제 Chrome에서 로그인·로그아웃·두 번째 계정 전환·공동 답변·승인을 수행했다.
- QA realm에서만 access token 수명을 12초로 줄여 갱신 POST 200과 SSE 재연결
  GET 200(`after=3`)을 연속 확인했다. 검증 후 300초로 복원하고 readback을 확인했다.
- 로그아웃 후 localStorage/sessionStorage에 토큰이 남지 않았다.
- 로그인 게이트와 조사·기록·SOP 세 화면을 데스크톱 1440px와 모바일 390px에서
  확인했다. 모바일 계정 헤더가 탐색 행과 겹치는 문제를 고쳤고, 세 화면 모두
  계정 컨트롤 겹침과 가로 overflow가 없었다. 기본 단일 테마 기준이다.

테스트 보조 HTTP 클라이언트는 localhost의 Secure 쿠키를 브라우저처럼 처리하도록
자체 임시 쿠키 jar만 조정했다. 앱·Keycloak 보안 설정을 우회하지 않았다.

## 범위와 남은 제한

- QA에는 OpenAI 키를 넣지 않았다. 사례·통계·exact-ID MCP 근거로 조사했고,
  SOP 의미 검색은 보고서에 사용 불가로 표시됐다. 유료 임베딩·재순위화나
  공유 RAG 변경·검색 품질 평가는 이번 인증 검증에 포함하지 않았다.
- 전체 Agent 재시작 DB suite·전체 MCP suite·Lighthouse 점수 평가는 실행하지 않았다.
  타입·빌드·명시한 회귀 검사와 실제 인증/조사 흐름의 통과 결과다.
- 편집기 LSP의 루트 Python 환경은 서비스 의존성을 찾지 못하고, Vue/TS/YAML LSP는
  설치되어 있지 않았다. 서비스별 basedpyright·vue-tsc와 Compose/nginx 검사로 확인했다.
- 역할/소유자별 인가·토큰 블랙리스트·운영용 Keycloak DB/TLS는 포함하지 않는다.
- 기존 PR #33과 브랜치는 보존했다. 이 작업에서 commit/push/PR/merge는 하지 않았다.

## 기본 계정 추가 검증 (2026-10-21)

사용자 요청으로 realm 초기화에 개발용 `test` / `test` 계정을 추가했다.
필수 프로필을 채우고 임시 비밀번호·required actions를 끄므로 첫 로그인에
비밀번호 변경이나 프로필 입력이 필요 없다.

- 별도 임시 Keycloak의 빈 저장소에서 realm을 가져와 계정 자동 생성을 확인했다.
- 새 realm과 기존 QA realm에서 각각 실제 Authorization Code + PKCE 로그인이 통과했다.
- 기존 앱의 작업·SOP API가 기본 계정으로 200을 반환했다.
- 실제 Chrome에서 `test` / `test` 로그인 후 조사 화면과 `Test User` 표시를 확인했다.
- Compose 설정·diff 공백 검사를 통과했다. 앱 코드 변경이 없어 전체 회귀 suite는 재실행하지 않았다.

기존 QA(18280)에도 계정을 추가했다. 다른 기존 볼륨은 realm import로 덮어쓰지
않으므로 관리자 화면에서 한 번 추가해야 한다. 신규 환경은 자동 생성한다.
