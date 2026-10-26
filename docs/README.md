# TRACE v1.0.0 문서

현재 기준은 **경보 기반 표준 Agent Server 조사**다. 모의 장비 경보가 Prometheus FDC 규칙에 걸리면 backend가 Agent Server에 thread를 만들고, 단일 ReAct Agent가 MCP 도구로 근거를 모아 원인 후보를 backend 업무 조사에 저장한다. 엔지니어는 화면에서 후보를 검증·대화·선택하고 실제 조치를 기록한다. 원인과 조치는 수치와 문서 근거를 보존한 확인 가설이다.

| 문서 | 내용 |
|---|---|
| [../README.md](../README.md) | 실행, 환경, 검증 명령, 이전 구성에서 이동 |
| [agent-server.md](agent-server.md) | Agent Server 실행·데이터 책임·API·Studio (현재 주 경로) |
| [agent.md](agent.md) | ReAct 그래프, 연결된 MCP 도구, Sensor·교육용 시뮬레이션 경계 |
| [agent-request.md](agent-request.md) | 경보 묶음 규칙, Agent 입력 봉투 `{role,content}`, 경보 텍스트 문법 |
| [architecture.md](architecture.md) | 서비스 구성, 저장 책임, 경보부터 조치 기록까지 |
| [api.md](api.md) | 신규 조사 API, Bearer 인증, 레거시 `/api/ai/*` 계약 |
| [frontend.md](frontend.md) | Vue 화면 구조, 호출 API, 목업 서버, 테스트 |
| [physics.md](physics.md) | Physics 계산·정량 분석·교육용 시뮬레이션 계약 |
| [mock-fab.md](mock-fab.md) | 합성 SECS/GEM 모의 장비, 수집기, Prometheus FDC 규칙 |
| [deploy.md](deploy.md) | develop 병합 후 Jenkins(EC2) 자동 배포 |
| [structure-review.md](structure-review.md) | 전체 경로 지도와 과거 구조 점검 기록 |
| [agent-experiments.md](agent-experiments.md) | LangSmith 추적·실험 가이드 |
| [sop-rag-retrieval-decision.md](sop-rag-retrieval-decision.md) | SOP 검색 방식(재순위화) 결정 기록 |
| [../deploy/keycloak/README.md](../deploy/keycloak/README.md) | Keycloak 계정 생성·URL·영속성 |
| [keycloak-validation.md](keycloak-validation.md) | Vue·backend 인증 이식 검증 기록 |
| [agent-server-validation.md](agent-server-validation.md) | Agent Server 실제 실행 검증 기록 |
| [v1-contract.md](v1-contract.md), [v1-validation.md](v1-validation.md), [v1-report.md](v1-report.md) | 레거시 v1 task 계약·검증·보고서 기록 |
| [idea_brief.html](idea_brief.html) | 과거 초기 기획 참고 자료; 현재 API 계약 아님 |

```text
compose.yaml                서비스 구성(keycloak, postgres, sop-postgres, seed, backend, MCP 4종, agent, web, prometheus)
frontend/                   Vue 3 + TS 화면(Vite), 목업 API(mock/)
backend/investigations_*.py 신규 조사·후보·승인·조치 기록 API
backend/agent_server_alerts.py  Prometheus 경보 → Agent Server thread·run 생성
backend/legacy_api.py, v1_*.py  레거시 /api/ai/* 작업·SSE·승인 이력, SOP 화면 API
agent/src/trace_agent/      표준 Agent Server(단일 ReAct 그래프, MCP 어댑터)
mcp/                        business/rag/physics/sensor MCP와 결정론적 계산
sop-ocap/                   SOP 3종·OCAP 19종 원문(SOP 화면·의미 검색 출처)
db/                         샘플 사례·문서·적재
fab/                        합성 SECS/GEM 모의 장비·수집기(별도 호스트, 별도 compose)
backend/prometheus/         Prometheus 수집 대상·FDC 규칙·규칙 테스트
deploy/                     nginx 프록시, Keycloak realm·로그인 테마
agent/tests/                ReAct 순환, thread 대화, 인증·후보·MCP 경계
backend/tests/              실제 PostgreSQL·HTTP 권한·승인·조치·경보 전달
tests/                      MCP 근거·물리·센서·시뮬레이션·SOP 검색
frontend/tests/             API 계약·스토어·렌더·목업
```

구형 `docker-compose*.yml`은 `compose.yaml` include wrapper다. 이전 다단계 agent와 CLI는 제거했다. 이전 localStorage 기록은 **로컬 읽기 전용**이며 서버 승인 이력으로 자동 전환하지 않는다.

샘플 데이터는 PHM이 아니다. 문서 조회는 정확한 문서 ID 조회와 `sop-ocap/` SOP·OCAP 의미 검색 두 가지다. Keycloak 로그인 사용자는 공동 작업하며 세부 역할·소유자별 인가는 후속 범위다.

문서 정리는 서비스 테스트 통과를 의미하지 않는다. 검증 실행 조건은 루트 README를 참고한다.
