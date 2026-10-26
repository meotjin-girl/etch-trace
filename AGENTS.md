# TRACE v1.0.0 PROJECT KNOWLEDGE BASE

## OVERVIEW

식각 이상 조사 시연 서비스. 단일 실행 구성은 `compose.yaml`이다.
새 기본 실행은 `agent/src/trace_agent/`의 표준 Agent Server다.
`/api/investigations`는 backend의 업무 조사·현재 후보·승인, `/agent/`는 대화·thread·run을 소유한다.
MCP는 에이전트 전용 도구다. 이전 v1 task API `/api/ai/*`는 레거시 호환 경로다.

## AGENT SERVER 계약

- 실행 방법: `docs/agent-server.md`. 실제 검증: `docs/agent-server-validation.md`.
- 경보 → thread 생성 → 초기 원인 후보 완성 → Business MCP로 업무 조사 신규 저장.
- 조사 ID와 thread ID는 1:1이며 동일 UUID다. 후속 후보는 같은 조사를 갱신한다.
- backend의 live 조사 모델·store·router는 `investigations_*` 모듈에 있다.
- 승인 시 검증된 로그인 사용자와 선택 후보 사본을 저장한다. 승인 뒤에도 대화는 계속된다. 조치 기록 전에는 선택을 취소하고 다시 고를 수 있다.
- Agent Server는 dev 로컬 체크포인트 볼륨, backend는 PostgreSQL 업무 데이터를 저장한다.
- 공개 대화 요청은 Keycloak Bearer, emitter 내부 요청은 내부 키를 사용한다.
- 새 경로는 레거시 `WAITING_INPUT`, `WAITING_APPROVAL`, command ID 계약을 따르지 않는다.
- 동일 경보 중복 방지와 저장 실패 재시도는 현재 요청 범위에서 제외한다.
- 아래 v1 상태·이벤트·스냅샷 규칙은 레거시 경로에 적용된다.
- 현재 Agent Server는 Business, RAG, Physics, Sensor MCP를 사용한다. Sensor 조회와 교육용 시뮬레이션은 사용자가 명시적으로 요청한 경우에만 결합한다.

## WHERE TO LOOK

| 작업 | 위치 | 계약 |
|---|---|---|
| 신규 조사·승인 API | `backend/investigations_api.py`, `investigations_models.py`, `investigations_store.py` | live 조사·후보·승인 사본 |
| Agent Server 그래프 | `agent/src/trace_agent/graph.py`, `nodes.py`, `tools.py`, `models.py` | 단일 ReAct agent↔ToolNode 순환, thread 기반 대화 |
| Agent MCP 어댑터 | `agent/src/trace_agent/evidence.py` | Business/RAG/Physics/Sensor MCP, 업무 DB 직접 조회 금지 |
| 레거시 공개 REST/SSE | `backend/legacy_api.py`, `backend/v1_*.py` | `/api/ai/tasks`, 질문 본문 `{question}` |
| 사례·통계 | `mcp/business.py`, `mcp/evidence.py` | backend 내부 사례 조회, 결정론적 계산 |
| 물리 계산 | `mcp/physics.py`, `mcp/physics_models.py` | 식각 깊이·평균 속도·선택비 계산 |
| Sensor MCP | `mcp/sensor.py`, `mcp/sensor_models.py` | 정확한 Run 식별자 기반 Mock Fab 시계열·불변 스냅샷 생성 |
| 정량·교육 시뮬레이션 | `mcp/quantitative_models.py`, `mcp/simulation_models.py` | 정상 Run 비교·R(t) 적분·미보정 Level 2/3 교육 모델 |
| 문서 | `mcp/rag.py` | exact-ID 문서 및 SOP/OCAP 의미 검색; 색인에는 `OPENAI_API_KEY` 필요 |
| 샘플 적재 | `db/seed.py`, `db/cases.json`, `db/documents.json` | PHM 아님, demo/source 표시 보존 |
| 화면 | `frontend/src/`, `docs/frontend.md` | 이상 로그 → AI 조사 → 원인 확인 → 조치 → 기록, 라이트·다크 자동. 이전 질문 화면은 `/legacy` |
| 로그인 화면 | `deploy/keycloak/themes/trace/` | Keycloak 로그인 테마, compose `KC_SPI_THEME__DEFAULT=trace` |
| SOP 화면 API | `backend/v1_sop.py` | `sop-ocap/` 표지 표·원문 파싱, `/api/sops` |
| 경로 지도 | `docs/structure-review.md` | 공개·내부 API, MCP 도구, 파일·데이터 경로 |
| 서비스 구성 | `compose.yaml`, `deploy/nginx.conf` | web 공개, backend·agent·MCP·DB 내부 네트워크 |
| 모의 장비·FDC | `fab/`, `backend/prometheus/`, `docs/mock-fab.md` | 합성 SECS/GEM 장비·수집기·Prometheus 규칙 기반 FDC |

## CONVENTIONS

- 루트 `pyproject.toml`은 개발 도구 설정이며 서비스별 런타임 의존성은 서비스 폴더가 소유한다.
- 공개 API는 Keycloak Bearer access token을 검증한다. 이름·역할 헤더와 URL 토큰은 인증 수단이 아니다.
- 로그인 사용자는 조사 내용을 공동으로 읽고 대화할 수 있으며 승인 시 backend가 검증한 사용자를 기록한다.
- 수치는 코드에서 계산하고 단위·근거 ID를 보존한다. 원인과 조치는 확인 가설이며 현재 원인의 확정이 아니다.
- Agent Server의 checkpoint는 `agent_dev_state` 볼륨, 업무 조사는 backend PostgreSQL에 저장된다.
- 레거시 `/api/ai/*` 경로의 상태·이벤트·command ID 규칙은 새 Agent Server 대화 경로에 적용하지 않는다.
- 일반 경보 조사에는 Sensor 기반 교육용 시뮬레이션을 자동 실행하거나 원인 근거로 섞지 않는다.

## COMMANDS AND COVERAGE

```bash
cp .env.example .env
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml up -d --build
uv sync --group dev
(cd agent && uv sync --group dev && uv run pytest)
(cd backend && uv sync --group dev && uv run pytest)
uv run --project mcp python -m unittest discover -s tests -p 'test_evidence.py' -v
uv run --project mcp --with pytest python -m pytest tests/test_physics.py -q
(cd frontend && npm ci && npm run type-check && npm test)
(cd fab && uv sync --group dev && uv run pytest)
(cd backend/prometheus && docker run --rm -v "$PWD":/w -w /w --entrypoint promtool prom/prometheus:v2.53.0 test rules rules_test.yml)
```

- `agent/tests/`: ReAct graph cycle, 동일 thread 대화 연속성, 인증·후보·MCP 경계 검증.
- `backend/tests/`: 실제 PostgreSQL과 HTTP 경계의 권한, 승인, 이벤트·SSE 및 조사 저장 검증. `TEST_DATABASE_URL` 필요.
- 루트·`mcp/`·`fab/` 테스트는 샘플 근거, 물리·센서 계산과 시뮬레이션을 검증한다.
- 위 목록은 커버리지 위치이며 테스트 통과 증거가 아니다. 문서 문구나 프롬프트 문장을 고정하는 자기 검증 테스트를 만들지 않는다.

## LEGACY AND SCOPE

이전 단일 조사 그래프는 `agent/` 루트의 구형 모듈이었으며 현재는 `agent/src/trace_agent/` 표준 Agent Server로 대체되었다.
`/api/ai/*` 호환 경로는 남아 있으나 신규 화면과 조사 흐름의 주 경로가 아니다.
장비·센서·정비 데이터에 대한 실제 조회 가능 범위는 연결된 MCP 구현과 도구에 한정한다.
