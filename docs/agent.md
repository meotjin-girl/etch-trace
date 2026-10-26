# TRACE Agent Server

기본 Agent Server 코드는 `agent/src/trace_agent/`에 있습니다. 단일 LangGraph가 ReAct 방식으로 모델과 MCP 도구를 순환시키고, 준비된 후보를 Business MCP를 통해 backend 업무 조사에 저장합니다. 전체 실행 계약과 실험 방법은 [Agent Server 안내](agent-server.md)를 참고하세요.

## 그래프와 책임

`agent/src/trace_agent/graph.py`는 `prepare → agent → tools → agent` 흐름을 구성합니다. 모델이 도구 호출을 요청하면 `ToolNode`가 실행하고, 도구 결과를 다시 모델에 전달합니다. 모델이 최종 제안을 만들면 `reason`과 `publish` 단계가 제안을 검증해 현재 조사에 저장합니다.

thread ID는 조사 ID와 같은 UUID입니다. Agent Server의 개발 체크포인트는 로컬 개발 볼륨에 저장되고, 업무 조사·후보·승인 정보는 backend가 PostgreSQL에 저장합니다. 승인은 원인 확정이 아니라 검토한 후보의 승인입니다.

## 현재 Agent에 연결된 MCP 도구

도구는 `agent/src/trace_agent/tools.py`에 선언되고 실제 MCP 전송은 `agent/src/trace_agent/evidence.py`가 담당합니다.

- Business MCP: `search_cases`, `analyze_metrics`, `list_investigations` 및 업무 조사 저장·조회
- RAG MCP: `search_documents`, `search_sop`
- Physics MCP: 기본 관계식, 정량 비교, R(t) 적분, 교육용 Level 1~3 시뮬레이션
- Sensor MCP: `analyze_current_etch_run`을 통한 정확한 Mock Fab Run 시계열 조회

각 도구는 실제 MCP 응답에 있는 근거를 사용합니다. 정량 계산은 결정론적 MCP 코드에서 수행하며, 모델이 없는 수치나 근거를 만들어내지 않도록 합니다.

## Sensor MCP와 교육용 시뮬레이션

`simulate_mock_fab_etch`는 사용자가 교육용 시뮬레이션을 명시적으로 요청한 경우에만 정확히 일치하는 완료 Run을 Sensor MCP에서 한 번 조회합니다. 장비·챔버·Lot·Wafer·Recipe와 선택적 Step/Run ID가 일치하지 않거나 식별할 수 없으면 다른 Run을 대입하지 않습니다. 조회한 `process_series`와 `snapshot_id`는 요청한 모든 패턴 폭 계산에 그대로 재사용합니다.

결과는 항상 `SIMULATED / NOT_VALIDATED` 교육용 가정이며 일반 경보 조사, 원인 확정, OCAP 판정, Recipe 변경 또는 Lot Release 근거로 사용하지 않습니다. 수집기 연결 실패, Run 불일치, GOOD 샘플 부족이면 안전하게 `INSUFFICIENT_DATA`를 반환합니다. 합성 Mock Fab 데이터는 실제 생산 장비의 원본 시계열이 아닙니다.

## 실행과 검증

루트 `.env`에 `OPENAI_API_KEY`, `OPENAI_MODEL`, `INTERNAL_API_KEY`를 설정하고 Compose를 실행합니다.

```sh
cp .env.example .env
docker compose -f compose.yaml up -d --build
```

Agent Server는 Compose 네트워크 안에서 backend, Business MCP, RAG MCP, Physics MCP, Sensor MCP와 통신합니다. Sensor MCP는 `FAB_COLLECTOR_URL`로 별도 Mock Fab Collector를 조회합니다.

Agent 테스트는 외부 모델 API를 호출하지 않고 모의 모델을 사용합니다.

```sh
cd agent
uv sync --group dev
uv run pytest -q
uv run ruff check .
uv run basedpyright
```

## 경계

Agent가 제시하는 원인과 조치는 확인 가설입니다. 실제 MES, 생산 장비 센서, 정비 API에 접근한다고 간주하면 안 됩니다. Sensor MCP가 조회 가능한 범위는 Mock Fab의 합성 데이터입니다.
