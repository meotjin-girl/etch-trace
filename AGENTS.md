# TRACE v1.0.0 PROJECT KNOWLEDGE BASE

## OVERVIEW

식각 이상 조사 시연 서비스. 단일 실행 구성은 `compose.yaml`이다. 브라우저는 backend만 호출하고, backend는 작업·신원·권한·검토·이벤트·승인 스냅샷을 소유한다. 유일한 LangGraph는 `agent/`에 있으며 MCP로 근거를 읽는다.

## WHERE TO LOOK

| 작업 | 위치 | 계약 |
|---|---|---|
| 통합 계약 | `docs/v1-contract.md` | 구현과 함께 읽고 차이는 명시 |
| 공개 REST/SSE | `backend/main.py` | `/api/ai/tasks`, 질문 본문 `{question}` |
| 목업 신원·권한 | `backend/v1_auth.py`, `v1_commands.py` | worker 본인 조회, engineer/admin 전체 조회, engineer만 검토 |
| 상태·메시지·검토·이벤트·스냅샷 | `backend/v1_store.py`, `v1_schema.sql` | DB 연결은 lifespan에서 열림 |
| 내부 명령 | `backend/v1_dispatch.py` | agent HTTP 실행·재개, command ID |
| 조사 그래프 | `agent/graph.py`, `query.py`, `models.py` | 접수·재질문·사례·통계·문서·보고서·검토 |
| MCP 어댑터 | `agent/evidence.py` | business/rag MCP만 사용, 업무 DB 직접 조회 금지 |
| 사례·계산 | `mcp/business.py`, `mcp/evidence.py` | backend `/internal/cases` 조회, 결정론적 통계 |
| 문서 | `mcp/rag.py` | `search_documents` exact-ID 조회와 `search_sop` SOP/WI/SPEC 벡터 검색. SOP 색인은 별도 `sop-postgres`에 저장하며 `OPENAI_API_KEY` 필요 |
| 샘플 적재 | `db/seed.py`, `cases.json`, `documents.json` | PHM 아님, demo/source 표시 보존 |
| 화면 | `frontend/app.js`, `frontend/api.js` | 공개 backend 연동, seq 기반 이벤트 복원 |
| 서비스 구성 | `compose.yaml`, `deploy/nginx.conf` | web만 공개 |

## CONVENTIONS

- 루트 `pyproject.toml`은 Python >=3.12 개발 도구 메타데이터이며 CLI export나 런타임 의존성을 중복 소유하지 않는다. 서비스별 환경을 사용한다.
- HTTP에는 URL 인코딩한 `X-User-Name`과 `X-User-Role`이 필수다. SSE는 `user_name`, `user_role` 쿼리를 사용한다. 실제 인증이 아니며 Keycloak은 후속 범위다.
- `/messages`는 소유자이면서 `WAITING_INPUT`일 때만, `/approval`은 engineer이면서 `WAITING_APPROVAL`일 때만 허용한다. admin은 검토 권한이 없다. 검토자 신원은 서버가 정한다.
- 상태: `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_APPROVAL`, `DONE`, `INCOMPLETE`, `FAILED`.
- 작업 ID가 그래프 thread ID다. PostgreSQL 체크포인트가 대기를 보존한다. backend 재시작은 대기 상태를 유지하고 중단된 QUEUED/RUNNING을 FAILED로 표시한다.
- backend 내부 API와 agent 실행은 `X-Internal-Key`를 사용한다. agent 실행과 backend 이벤트 콜백에는 동일한 `X-Command-ID`도 필수다. agent는 현재 명령 ID를 실행 config에서 콜백으로 전달한다.
- 수치는 코드에서 계산하고 단위·근거 사례 ID를 보존한다. 원인과 조치는 확인 가설이며 문서 조항과 연결한다. 보고서 `demo:true`를 유지한다.
- 검토 전에도 작업·초안·메시지·이벤트는 저장된다. 승인된 스냅샷만 `v1_investigations`에 남는다. 이력을 다음 조사의 근거로 검색하는 기능은 미구현이다.
- 이전 localStorage 기록은 로컬 읽기 전용이다. 서버 기록으로 자동 이관하거나 승인된 것으로 취급하지 않는다.

## COMMANDS AND COVERAGE

```bash
cp .env.example .env
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml up -d --build
uv sync --group dev
(cd agent && uv sync --group dev && uv run pytest)
(cd backend && uv sync --group dev && uv run pytest)
uv run --project mcp python -m unittest discover -s tests -p 'test_evidence.py' -v
node --test frontend/frontend.test.mjs
```

- `agent/tests/`: 질문 추출·보완, 재질문, 수정·승인, 근거 보존, 콜백 replay, PostgreSQL 프로세스 재시작(`AGENT_TEST_DATABASE_URL` 필요).
- `backend/tests/`: 실제 PostgreSQL과 HTTP 경계로 권한, 대기 상태, 검토 경쟁, 승인 스냅샷, 이벤트·SSE replay, 실패·재시작 검증. `TEST_DATABASE_URL` 필요(기본 `postgresql:///postgres`).
- `tests/test_evidence.py`: 샘플·유사도·통계·MCP 경계 검증. DB 검증에는 `EVIDENCE_TEST_DATABASE_URL` 필요.
- 이 목록은 커버리지 위치이며 테스트 통과 증거가 아니다. 문서 문구나 프롬프트 문장을 고정하는 자기 검증 테스트를 만들지 않는다.

## LEGACY AND SCOPE

이전 CLI 소스·입력 예제·`tests/test_workflow.py`는 v1 서비스 커버리지 확인 후 제거했다. CLI 입력 루프·출력 플래그·선택적 기록 제안은 v1 계약에서 폐기했다. `docker-compose*.yml`은 `compose.yaml` include wrapper일 뿐 별도 서비스를 정의하지 않는다.

이전 backend 그래프·도구·DB 모듈과 PHM 전용 스크립트는 제거했다. 이전 구현은 Git 이력에서 확인한다. 하위 `backend/AGENTS.md`는 현재 v1 API·상태·명령 계약을 설명한다.

장비/공정 분류별 서브그래프, 자동 담당자 배정, Keycloak, 승인 이력 근거 검색을 구현된 기능으로 문서화하지 않는다. PHM 표준화 값에 물리 단위를 붙이거나 정비 정지 시각을 발생 시각으로 간주하지 않는다.
