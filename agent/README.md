# TRACE Agent 안내

실제 조사 그래프 흐름과 데이터 한계는 [한국어 Agent 설명](../docs/development/agent.md)을 기준으로 확인하세요.

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
| `agents/scope_agent.py` | Business MCP 데모 사례와 요청자 권한으로 조회한 승인 조사 이력 중 유사한 최대 3건을 확인 |
| `agents/comparison_agent.py` | Business MCP 통계 도구로 입력 계측값을 데모 사례와 비교 |
| `agents/sensor_agent.py` | 입력값과 실제 센서 시계열을 구분. 센서 MCP가 없으면 미확인 표시 |
| `agents/maintenance_agent.py` | 정비 이력 MCP가 아직 없어 조회 불가 상태 표시 |
| `agents/recommendation_agent.py` | 사례 문서 ID exact 조회와 자연어 SOP RAG 검색을 모두 호출해 원인 후보·문서 기반 점검 순서 정리 |
| `agents/common.py` | 각 하위 그래프의 근거 수집→역할 추론 구조와 선택적 LLM 호출을 공통 제공 |
| `evidence.py` | Business/RAG MCP의 사례·통계·문서·SOP 의미 검색·승인 이력 도구 호출부 |
| `main.py` | 엔지니어 승인 뒤 Business MCP `save_investigation` 호출 |
| `models.py` | 에이전트 간 전달되는 조사 단계·근거·보고서 자료 형식 |

Agent의 구조화 문구 분석은 `OPENAI_API_KEY`와 `OPENAI_MODEL` 설정이 모두 있을 때 에이전트별로 최대 한 번 실행합니다. 별도의 SOP RAG MCP는 `OPENAI_API_KEY`로 query embedding과 조항 재순위화를 실행하므로, 키가 없거나 MCP 호출이 실패하면 의미 검색을 수행했다고 표시하지 않고 미확인 사유를 보고합니다. 첫 SOP 검색 시에는 문서 인덱스가 생성되며 문서 변경이 없으면 임베딩은 재사용됩니다.

추천 에이전트는 기존 RAG MCP의 `search_documents(document_ids)` 정확 ID 조회와 `search_sop(query)` 자연어 검색을 모두 호출합니다. 후자는 기존 `sop_chunks.py`, `sop_vectors.py`, `sop_rerank.py`를 사용해 SOP/WI/SPEC 후보 20개를 찾고 3개 조항을 재순위화합니다. Compose는 분리된 `sop-postgres`와 문서 폴더 mount를 제공하며, 첫 요청이 현재 조항 색인을 자동으로 적재합니다. 센서 시계열과 정비 이력의 전용 MCP는 아직 없으므로 확인 불가로 표시합니다. 승인 이력은 Backend가 저장한 요청자 신원으로 권한 필터 후 참고하며, 기존 근거 metadata를 보고서까지 보존합니다.
