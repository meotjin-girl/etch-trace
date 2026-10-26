# BACKEND KNOWLEDGE BASE

## OVERVIEW

업무 조사·후보·승인과 레거시 v1 작업·이벤트 영속화 경계다.
LangGraph 실행은 별도 `agent/` Agent Server가 담당한다.
`main.py`는 lifespan과 router 조합, `api_dependencies.py`는 공유 인증·runtime,
`legacy_api.py`는 기존 v1 경로를 소유한다.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 새 조사·후보·승인 | `investigations_api.py`, `investigations_models.py`, `investigations_store.py` | `/api/investigations`; 초기 제안 후 생성, thread와 같은 UUID. 조치 기록 전 승인 취소(`DELETE …/approval`) 가능, 승인 후 `/action`으로 조치 기록 1회 |
| 새 조사 DB | `investigations_schema.sql` | 현재 후보 갱신과 승인 사본 보존 |
| Agent Server 경보 전달 | `agent_server_alerts.py` | `AGENT_SERVER_URL` 설정 시 thread/run 생성, 레거시 task 생성 안 함 |
| 레거시 요청·SSE·승인 | `legacy_api.py` | 기존 `/api/ai/*` 계약 보존 |
| 경계 데이터 모델 | `v1_models.py` | API·콜백·스냅샷 |
| DB 접속·이벤트 | `v1_store.py`, `v1_schema.sql` | lifespan에서 풀 초기화 |
| 명령과 상태 전이 | `v1_commands.py` | 작업 행 잠금과 명령 ID 검사 |
| Agent HTTP 호출 | `v1_dispatch.py` | 전달 실패는 FAILED로 기록 |
| 로그인·공동 작업 인가 | `v1_auth.py` | Keycloak JWKS·RS256·issuer·audience·expiry 검증 |
| 승인 이력·SOP 화면 API | `main.py`, `v1_store.py`, `v1_sop.py` | `/api/ai/investigations`는 `Store.investigations` 재사용, `/api/sops`는 `SOP_DOCUMENTS_DIR`(compose `sop-ocap/`) |
| 회귀 테스트 | `tests/` | 실제 PostgreSQL 격리 스키마 |
| 실제 서비스 흐름 | `../tests/check_agent_server.mjs` | 새 전체 스택, 실제 Keycloak PKCE·AI·MCP; `check_stack.py`는 레거시 |

## CONVENTIONS

- 서버 모듈은 이 디렉터리에서 실행한다: `uv run uvicorn main:app --port 8000`.
- 업무 테이블은 `v1_` 접두사로 기존 PHM 테이블과 분리한다.
- 새 live 조사는 `v1_live_investigations`에 저장한다. 동일 thread의 후속 저장은 후보 목록을 교체하고 revision을 증가시킨다.
- 승인은 토큰의 사용자와 현재 후보 사본을 한 트랜잭션에 기록한다. 승인 후에도 대화·후보 갱신은 가능하며 승인 사본은 바뀌지 않는다.
- `WAITING_INPUT`·`WAITING_APPROVAL` 조건은 레거시 경로에만 적용한다.
- 이벤트 기록은 작업 행 잠금을 먼저 확보하며 명령별 event_id로 중복 제거한다.
- 로그인한 사용자는 모든 작업을 읽고 대기 작업에 답변·검토할 수 있다. 역할·소유자별 분리는 후속 범위다.
- 인증을 목록·상세·이벤트·SSE·승인 이력·SOP에 동일하게 적용한다. SSE는 Bearer 헤더로 연결하고 토큰 만료 시 닫는다.
- 작업·발화·검토·승인 스냅샷에 서버가 검증한 `sub`를 보존한다. 과거 목업 기록의 ID는 null이며 이름으로 계정을 추정하지 않는다.

## ANTI-PATTERNS

- Agent나 MCP에 승인 스냅샷의 DB 쓰기 권한을 넘기지 않는다.
- 콜백의 내부 키와 명령 ID 검사를 생략하지 않는다.
- 이름 입력값이나 브라우저 로컬 기록을 검증된 인증·승인으로 취급하지 않는다.
- 표준화 PHM 센서와 v1 샘플 사례의 물리 단위 값을 혼합하지 않는다.
