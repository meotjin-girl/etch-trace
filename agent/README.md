# TRACE Agent 안내

실제 조사 그래프 흐름과 데이터 한계는 [한국어 Agent 설명](../docs/agent.md)을 기준으로 확인하세요.

## 실행

저장소 루트에서 실행합니다.

```sh
cp .env.example .env
# 필요하면 .env에 OPENAI_API_KEY와 OPENAI_MODEL을 설정
# 루트 디렉터리에서 실행
docker compose -f compose.yaml up -d --build
```

화면은 `http://localhost:8080`에서 확인합니다. 로그는 `docker compose -f compose.yaml logs -f agent backend`, 종료는 `docker compose -f compose.yaml down`입니다.

## 다섯 에이전트와 주요 파일

| 파일 | 역할 |
|---|---|
| `graph.py` | 조사 접수·보완·검토를 관리하는 Supervisor 그래프. 아래 다섯 하위 그래프를 순서대로 호출 |
| `agents/scope_agent.py` | Business MCP의 데모 사례로 문제 범위를 확인 |
| `agents/comparison_agent.py` | Business MCP 통계 도구로 입력 계측값을 데모 사례와 비교 |
| `agents/sensor_agent.py` | 입력값과 실제 센서 시계열을 구분. 센서 MCP가 없으면 미확인 표시 |
| `agents/maintenance_agent.py` | 정비 이력 MCP가 아직 없어 조회 불가 상태 표시 |
| `agents/recommendation_agent.py` | 관련 사례와 RAG MCP 문서로 원인 후보·점검 순서 정리 |
| `agents/common.py` | 각 하위 그래프의 근거 수집→역할 추론 구조와 선택적 LLM 호출을 공통 제공 |
| `provisional_sop.py` | 승인된 SOP 검색이 준비되기 전까지 사용하는 압력 조사용 고정 임시 체크리스트. 에이전트가 아님 |
| `models.py` | 에이전트 간 전달되는 조사 단계·근거·보고서 자료 형식 |

OpenAI 설정 두 항목이 모두 없으면 다섯 하위 그래프는 규칙 기반 결과를 내며 외부 LLM API를 호출하지 않습니다. 두 항목이 있으면 에이전트별로 구조화 응답을 한 번 요청합니다. 이 경우 조사 1건에서 최대 다섯 번 모델 요청이 발생할 수 있습니다. 모델 결과는 데모 사례·통계·문서 근거를 대체하지 않습니다.

실제 MES Run, 센서 시계열, 정비 기록 MCP는 아직 연결되어 있지 않습니다. 해당 에이전트는 자료를 임의로 만들지 않고 미확인 상태를 반환합니다. 테스트 파일은 이번 변경에서 수정하지 않았습니다.
