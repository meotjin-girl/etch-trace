# TRACE 문서

식각 공정 이상 **조사** AI Agent. 사용자가 이상 현상을 입력하면 **장비 이상 / 공정 이상 / 불명확**으로 분류하고, 분기별 조사 에이전트가 데이터·문서 근거를 모아 보고서를 쓴다. 공정 엔지니어가 승인해야 저장된다.

| 문서 | 내용 | 주 독자 |
|---|---|---|
| [architecture.md](architecture.md) | 시스템 구성도, 요청 시퀀스, 배포 | 전원 |
| [agent.md](agent.md) | 메인 그래프, 분기별 서브그래프 단계, State, 도구 | 에이전트 담당 |
| [api.md](api.md) | REST API · SSE 이벤트 명세 | **프론트 담당** |
| [idea_brief.html](idea_brief.html) | 팀 초기 기획서 | 참고 |

## 파일 트리

```
etch-trace/
├─ README.md                  # 실행·배포 방법
├─ docs/                      # 설계 문서
│  ├─ README.md               #   목차 + 파일 트리 + 작업 단계
│  ├─ architecture.md         #   시스템 구성 Mermaid
│  ├─ agent.md                #   에이전트 그래프 Mermaid
│  ├─ api.md                  #   프론트 연동 API 명세
│  └─ idea_brief.html         #   팀 초기 기획서
├─ frontend/                  # 웹 화면 (정적 HTML·CSS·JS, nginx가 서빙)
│  ├─ index.html
│  ├─ app.js
│  └─ styles.css
├─ backend/                   # FastAPI + LangGraph 조사 에이전트 (API 서버)
│  ├─ main.py                 #   REST API · SSE  ← api.md 와 1:1
│  ├─ graph.py                #   메인 그래프: classify → 분기 → verify → summarize → HITL
│  ├─ branches.py             # 🆕 분기별 서브그래프 (장비 / 공정 / 불명확)
│  ├─ tools.py                #   조사 도구 (숫자 계산은 전부 여기)
│  ├─ db.py                   #   DB 연결 · 이벤트 기록
│  ├─ schema.sql              #   테이블 정의 (+ 🆕 engineers, tasks.category·assignee)
│  ├─ prompts/                #   LLM 지시문 (코드와 분리해 버전 관리)
│  │  ├─ classify.md          # 🆕 분류 기준
│  │  ├─ plan_equipment.md    # 🆕 장비 에이전트
│  │  ├─ plan_process.md      # 🆕 공정 에이전트 (기존 plan.md)
│  │  └─ summarize.md         #   보고서 형식
│  ├─ knowledge/              #   RAG 원문 (*.md → pgvector)
│  ├─ ingest_phm.py           #   PHM 2018 CSV 적재
│  ├─ index_docs.py           #   knowledge 임베딩 색인
│  ├─ e2e_check.py            #   API 전체 흐름 점검
│  └─ Dockerfile
├─ src/etch_investigator/     # dev 초기 프로토타입 (CLI · JSON 샘플)
├─ tests/  examples/  pyproject.toml   # 프로토타입용
├─ deploy/nginx.conf          # :80 → frontend 정적 파일 + /api → agent(backend):8000
├─ docker-compose.yml         # 로컬: postgres(pgvector) 하나
└─ docker-compose.prod.yml    # 서버: postgres + backend + nginx
```
`frontend/`는 [api.md](api.md)의 REST API로만 백엔드와 통신한다 (현재 화면은 목업 데이터, API 연동 예정).
`src/etch_investigator/`는 dev 브랜치의 초기 LangGraph 프로토타입(CLI, JSON 샘플)으로, 원본 README의 사용법 그대로 동작한다.

## 오늘 작업 단계

| # | 작업 | 산출물 | 완료 기준 |
|---|---|---|---|
| 1 | 문서·파일 트리 정리 | `docs/*` | 팀이 api.md 보고 연동 시작 가능 |
| 2 | 장비용 도구 2개 | `tools.py`: `fault_history`, `signal_trend` | `uv run python tools.py` 통과 |
| 3 | 대화형 접수: 정보 추출 + 재질문 | `graph.py`: `intake`, `ask` · `POST /messages` | run_id 없이 요청 → QUESTION → 답변 → 진행 |
| 4 | 분류 + 분기 서브그래프 + 분류 검증 | `graph.py`, `branches.py`, `prompts/*` | 장비·공정 run 각 1건이 다른 분기로 감 |
| 5 | 담당자 배정 + 접근 제한 | `engineers` 테이블, `assign` 노드, `main.py` 권한 | 비배정 엔지니어 조회 404 · 승인 403, 분류 정정 시 재배정 |
| 6 | API 마무리: 새 필드·이벤트, CORS, 관리자 배정 | `main.py`, `schema.sql` | `e2e_check.py` 통과 |
| 7 | 서버 재배포 | EC2 | 외부에서 `/api/ai/tasks` 호출 성공 |

나중에(오늘 범위 밖): MCP 서버 분리, Spring Boot 게이트웨이, Supabase 인증, Kafka 대기열, 장비 데이터 추가 적재.
