# BACKEND KNOWLEDGE BASE

## OVERVIEW

현재 DB 기반 API/에이전트 경계다. 점수 10: 코드 비율, 자체 설정, 많은 심볼·공개 함수, `db.q`의 높은 참조 중심성.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 요청 생성·조회·SSE·승인 | `main.py` | `TaskIn`에 `tool`, `run_id`, `question` 필수 |
| 그래프 실행·중단·재개 | `graph.py` | `run()`이 상태와 이벤트 기록 |
| DB 접속·이벤트 | `db.py`, `schema.sql` | `db.init()`는 앱 생성 시 호출 |
| 조사 도구·통계 | `tools.py` | `TOOLS`는 LLM에 허용된 네 도구 |
| 공정 데이터 적재 | `ingest_phm.py` | run ID는 `{runnum}-{Lot}` |
| 문서 벡터 색인 | `index_docs.py`, `knowledge/*.md` | `## ` 단위 chunk |
| 계획·보고서 지시문 | `prompts/plan.md`, `prompts/summarize.md` | 그래프에서 파일을 직접 읽음 |
| 실제 서버 흐름 점검 | `e2e_check.py` | API 실행 및 적재된 DB 필요 |

## CONVENTIONS

- 서버 모듈은 이 디렉터리에서 실행한다: `uv run uvicorn main:app --port 8000`. `main.py`가 `db.init()`를, `graph.py`가 체크포인터 설정을 import 시 수행한다.
- `db.q`는 autocommit 풀의 SQL 진입점. 상태는 `tasks`, 이벤트는 `task_events`, 승인된 결과는 `investigations`에 기록한다.
- 그래프 한도는 8턴, 120초, 같은 도구 3회. 키가 없거나 LLM 호출이 실패하면 고정 도구 순서와 템플릿 보고서로 이어간다.
- `get_run_context`는 대상 run 종료 이전 고장만 조회하고, `find_reference_runs`는 같은 recipe의 이전 run 중 고장 직전 24시간을 제외한다.
- 현재 엔지니어 역할 검사와 배정 엔지니어 검증은 같은 것이 아니다. 향후 배정 접근 규칙은 `docs/agent.md`에 설계되어 있지만 코드에는 아직 없다.

## ANTI-PATTERNS

- `save_investigation`을 `TOOLS`에 등록하지 않는다. `finalize_node`에서 승인 여부를 확인한 뒤에만 저장한다.
- `docs/api.md`의 선택적 `tool`/`run_id` 및 재질문 경로를 구현된 요청 계약으로 취급하지 않는다.
- 표준화 센서값에 임의 단위를 붙이거나 정비 정지 시각을 실제 고장 발생 시각이라고 말하지 않는다.
- `prompts/plan.md`의 도구 1회씩 호출·숫자 비생성 규칙과 `prompts/summarize.md`의 불확실성 표현을 거스르지 않는다.
