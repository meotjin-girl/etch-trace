# BACKEND KNOWLEDGE BASE

## OVERVIEW

v1 공개 API와 작업·검토·이벤트 영속화 경계다. LangGraph 실행은 별도 `agent/` 서비스만 담당한다.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 요청 생성·조회·SSE·승인 | `main.py` | 생성에는 question만 필수 |
| 경계 데이터 모델 | `v1_models.py` | API·콜백·스냅샷 |
| DB 접속·이벤트 | `v1_store.py`, `v1_schema.sql` | lifespan에서 풀 초기화 |
| 명령과 상태 전이 | `v1_commands.py` | 작업 행 잠금과 명령 ID 검사 |
| Agent HTTP 호출 | `v1_dispatch.py` | 전달 실패는 FAILED로 기록 |
| 목업 신원·권한 | `v1_auth.py` | 이름과 역할; Keycloak 후속 |
| 승인 이력·SOP 화면 API | `main.py`, `v1_store.py`, `v1_sop.py` | `/api/ai/investigations`는 `Store.investigations` 재사용, `/api/sops`는 `SOP_DOCUMENTS_DIR`(compose `sop-ocap/`) |
| 회귀 테스트 | `tests/` | 실제 PostgreSQL 격리 스키마 |
| 실제 서비스 흐름 | `../tests/check_stack.py` | 실행 중인 전체 스택 필요 |

## CONVENTIONS

- 서버 모듈은 이 디렉터리에서 실행한다: `uv run uvicorn main:app --port 8000`.
- 업무 테이블은 `v1_` 접두사로 기존 PHM 테이블과 분리한다.
- 이벤트 기록은 작업 행 잠금을 먼저 확보하며 명령별 event_id로 중복 제거한다.
- 추가 답변은 요청자만, 검토는 어느 엔지니어든 가능하다. 담당자 배정은 없다.
- 읽기 권한을 목록·상세·이벤트·SSE에서 동일하게 적용한다.

## ANTI-PATTERNS

- Agent나 MCP에 승인 스냅샷의 DB 쓰기 권한을 넘기지 않는다.
- 콜백의 내부 키와 명령 ID 검사를 생략하지 않는다.
- 이름 입력값이나 브라우저 로컬 기록을 검증된 인증·승인으로 취급하지 않는다.
- 표준화 PHM 센서와 v1 샘플 사례의 물리 단위 값을 혼합하지 않는다.
