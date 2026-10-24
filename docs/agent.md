# TRACE Agent Server

기본 Agent Server 코드는 `agent/src/trace_agent/`에 있습니다. 단일 LangGraph가 ReAct 방식으로 모델과 MCP 도구를 순환시키고, 준비된 후보를 Business MCP를 통해 backend 업무 조사에 저장합니다. 전체 실행 계약과 실험 방법은 [Agent Server 안내](agent-server.md)를 참고하세요.

## 그래프와 책임

`agent/src/trace_agent/graph.py`는 `prepare → agent → tools → agent` 흐름을 구성합니다. 모델이 도구 호출을 요청하면 `ToolNode`가 실행하고, 도구 결과를 다시 모델에 전달합니다. 모델이 최종 제안을 만들면 `reason`과 `publish` 단계가 제안을 검증해 현재 조사에 저장합니다.

thread ID는 조사 ID와 같은 UUID입니다. Agent Server의 개발 체크포인트는 로컬 개발 볼륨에 저장되고, 업무 조사·후보·승인 정보는 backend가 PostgreSQL에 저장합니다. 승인은 원인 확정이 아니라 검토한 후보의 승인입니다.

## 현재 Agent에 연결된 MCP 도구

도구는 `agent/src/trace_agent/tools.py`에 선언되고 실제 MCP 전송은 `agent/src/trace_agent/evidence.py`가 담당합니다.

- Business MCP: `search_cases`, `analyze_metrics`, `list_investigations` 및 업무 조사 저장·조회
- RAG MCP: `search_documents`, `search_sop`
- Physics MCP: `evaluate_etch_physics`

각 도구는 실제 MCP 응답에 있는 근거를 사용합니다. 정량 계산은 결정론적 MCP 코드에서 수행하며, 모델이 없는 수치나 근거를 만들어내지 않도록 합니다.

## 아직 연결하지 않은 Sensor MCP

`mcp/sensor.py`와 `mcp/sensor_models.py`에는 Mock Fab의 센서 시계열을 조회·분석하는 Sensor MCP가 구현되어 있고, `compose.yaml`에서 별도 `sensor-mcp` 서비스로 실행할 수 있습니다. 다만 현재 Agent의 `tools.py`, `evidence.py`, 설정과 실행 의존성에는 Sensor MCP 연결을 추가하지 않았습니다. 따라서 Sensor MCP가 실행 중이어도 Agent의 조사 결과에는 사용되지 않습니다. Agent 연동은 별도 변경 범위입니다.

Sensor MCP의 수집기가 없거나 데이터가 일치하지 않으면 도구는 충분한 데이터가 없다고 응답합니다. 합성 Mock Fab 데이터는 실제 생산 장비의 원본 시계열이 아닙니다.

## 실행과 검증

루트 `.env`에 `OPENAI_API_KEY`, `OPENAI_MODEL`, `INTERNAL_API_KEY`를 설정하고 Compose를 실행합니다.

```sh
cp .env.example .env
docker compose -f compose.yaml up -d --build
```

Agent Server는 Compose 네트워크 안에서 backend, Business MCP, RAG MCP, Physics MCP와 통신합니다. Sensor MCP는 현재 Agent 의존성에 포함되지 않습니다.

Agent 테스트는 외부 모델 API를 호출하지 않고 모의 모델을 사용합니다.

```sh
cd agent
uv sync --group dev
uv run pytest -q
uv run ruff check .
uv run basedpyright
```

## 경계

Agent가 제시하는 원인과 조치는 확인 가설입니다. 실제 MES, 생산 장비 센서, 정비 API에 접근한다고 간주하면 안 됩니다. Sensor MCP가 조회 가능한 범위는 Mock Fab의 합성 데이터이며, 이 MCP를 Agent에 연결하는 것은 아직 구현되지 않았습니다.
