# PROJECT KNOWLEDGE BASE

**Generated:** 2026-10-20
**Commit:** 13204d0
**Branch:** dev_backend

## OVERVIEW

식각 공정 이상을 근거 기반으로 조사하는 프로젝트. 현재 런타임은 PostgreSQL/pgvector를 쓰는 FastAPI + LangGraph 백엔드, 브라우저 내 샘플 데이터로 동작하는 정적 프론트엔드, 별도의 JSON 사례 기반 CLI 프로토타입으로 나뉜다.

## STRUCTURE

```text
etch-trace/
├── backend/                 # DB 기반 REST/SSE 조사 서비스와 적재·색인
│   ├── knowledge/           # pgvector에 색인할 문서 원문
│   └── prompts/             # 계획과 보고서 생성 지시문
├── frontend/                # API 미연결 정적 데모; 브라우저 localStorage 기록
├── src/etch_investigator/   # 별개 CLI 프로토타입 패키지
│   └── data/                # 프로토타입 사례·문서 JSON
├── tests/                   # CLI 프로토타입 워크플로 테스트
├── examples/                # CLI 입력 JSON
├── docs/                    # 설계 및 목표 API 계약 (일부 미구현)
├── deploy/nginx.conf        # /api 프록시와 정적 파일 서빙
├── docker-compose.yml       # 로컬 PostgreSQL만
└── docker-compose.prod.yml  # nginx, agent, PostgreSQL
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 실제 REST/SSE 요청과 권한 | `backend/main.py` | 목업 `X-User-*` 인증; 시작 시 DB 초기화 |
| 조사/승인 그래프 | `backend/graph.py` | 독립 프로토타입 그래프와 혼동 금지 |
| SQL·계측값·문서 조회 | `backend/tools.py`, `backend/db.py`, `backend/schema.sql` | 수치 계산은 코드에서 수행 |
| 문서 색인·PHM 적재 | `backend/index_docs.py`, `backend/ingest_phm.py` | 실행 전 데이터와 DB 필요 |
| 데모 UI 동작 | `frontend/app.js`, `frontend/index.html` | API 호출 대신 하드코딩된 사례 사용 |
| CLI 질문/승인 흐름 | `src/etch_investigator/`, `tests/test_workflow.py` | 별도 패키지 설정은 루트 `pyproject.toml` |
| 의도된 미래 계약 | `docs/api.md`, `docs/agent.md` | 구현 여부는 실제 코드에서 확인 |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `app` | FastAPI | `backend/main.py:21` | 9 | 실제 HTTP 라우트 |
| `run` | function | `backend/graph.py:219` | 3 | 백그라운드 조사·재개 |
| `q` | function | `backend/db.py:16` | 31 | 서비스 SQL 공통 진입점 |
| `compare_signals` | function | `backend/tools.py:52` | 4 | step별 참조 run z-score |
| `build_graph` | function | `src/etch_investigator/graph.py:158` | 8 | 배치/기록 CLI 그래프 |
| `InvestigationRepository` | class | `src/etch_investigator/repository.py:12` | 10 | JSON 사례 검색 |

## CONVENTIONS

- 루트 `pyproject.toml`은 Python >=3.11 CLI 패키지, `backend/pyproject.toml`은 Python >=3.12 서버 프로젝트다. 테스트 명령과 의존성 설치 위치가 다르다.
- 백엔드는 현재 `tool`과 `run_id`가 필수인 요청을 받는다. `docs/api.md`의 자유문장 요청·재질문·분류·담당자 배정은 아직 구현된 API로 간주하지 않는다.
- `frontend/app.js`는 샘플 사례의 유사도·수치 분석을 브라우저에서 실행하고 승인 기록을 `localStorage`에 저장한다. 서버 조사 결과와 자동 동기화되지 않는다.
- 백엔드의 `task_events` 행이 SSE 이벤트가 되고, 승인 시 LangGraph의 동일 `thread_id`를 `Command(resume=...)`로 재개한다.

## ANTI-PATTERNS (THIS PROJECT)

- 수치를 LLM에게 계산시키거나 원인을 확정적으로 쓰지 않는다. 수치에는 run/사례 ID, 원인·조치에는 문서 조항을 붙인다.
- `save_investigation`을 LLM 도구 목록에 넣거나 승인 전에 호출하지 않는다.
- 설계 문서에 있는 미구현 `branches.py`, 분류용 프롬프트, `/messages` 경로를 현재 코드의 일부로 가정하지 않는다.
- PHM 센서 표준화 값에 물리 단위를 붙이거나 고장 기록의 정지 시각을 발생 시각으로 단정하지 않는다.

## UNIQUE STYLES

- `backend/knowledge/*.md`는 `## ` 제목별로 분리되어 임베딩된다. 이 섹션 구조가 색인 단위다.
- API/SSE는 `/api/ai/tasks`를 중심으로 하며, 데모 인증의 한글 이름은 URL 인코딩해 전달한다.

## COMMANDS

```bash
docker compose up -d
cd backend && uv sync
uv run python ingest_phm.py ../data/phm_data_challenge_2018/train/01_M01_DC_train.csv
uv run python index_docs.py
uv run uvicorn main:app --port 8000
uv run python tools.py                 # 실데이터/DB 필요
uv run python e2e_check.py             # 실행 중인 API/DB 필요
cd ..
python3 -m http.server -d frontend 5173
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## NOTES

- 백엔드 모듈 import 시 DB 풀이 열리고 그래프의 PostgreSQL 체크포인터가 설정된다. 백엔드 검증에는 PostgreSQL 접속이 필요하다.
- `OPENAI_API_KEY`가 없으면 백엔드 계획과 보고서는 고정 순서·템플릿으로 폴백하지만 문서 임베딩 색인은 키를 요구한다.
- 서버 배포에서 공개 포트는 nginx `80`이며 agent `8000`과 PostgreSQL `5432`는 내부 네트워크에만 둔다.
