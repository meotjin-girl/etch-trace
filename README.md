# etch-trace — 식각 공정 이상 조사 AI Agent

사용자가 식각 이상 현상을 입력하면 **장비 이상 / 공정 이상 / 불명확**으로 분류하고, 분기별 조사 에이전트가 공정 데이터·과거 사례·문서 근거를 모아 보고서를 작성합니다. 원인은 단정하지 않고 "우선 확인 가설"로 제시하며, 공정 엔지니어가 승인한 기록만 저장합니다.

설계 문서: [docs/README.md](docs/README.md) — 파일 트리, 작업 단계, 아키텍처·에이전트 설계, **프론트 연동 API 명세 [docs/api.md](docs/api.md)**

| 폴더 | 내용 |
|---|---|
| `frontend/` | 웹 화면 (정적 HTML·CSS·JS) |
| `backend/` | FastAPI + LangGraph 조사 에이전트, REST API · SSE, PostgreSQL/pgvector |
| `docs/` | 설계 문서 |
| `src/etch_investigator/`, `tests/`, `examples/` | 초기 LangGraph 프로토타입 (CLI, JSON 샘플) |
| `deploy/`, `docker-compose*.yml` | 로컬 DB, 서버 배포 구성 |

## 조사 흐름

```text
사용자 질문 → 분류(장비 / 공정 / 불명확)
                 ├─ 장비: run 정보 → 고장 이력 → 센서 추세 → 정비 문서
                 ├─ 공정: run 정보 → 같은 레시피 정상 run → step별 z-score → 공정 문서
                 └─ 불명확: 두 분기를 절반 예산으로
           → 분류 검증(근거가 반대면 1회 재분류) → 보고서 → 엔지니어 승인/수정 → 저장
```

- 재질문·승인에는 LangGraph `interrupt()` / `Command(resume=...)`를 사용하고, 체크포인트는 PostgreSQL에 저장합니다.
- 수치(z-score, 추세)는 코드가 계산하고 LLM은 분류·도구 선택·문장 작성만 합니다.
- 모든 수치 판단에는 원천 run/사례 ID, 원인/조치에는 문서 조항을 연결합니다.

## 백엔드 실행 (`backend/`)

```bash
docker compose up -d                       # PostgreSQL 16 + pgvector
cd backend && uv sync
# 데이터: data/phm_data_challenge_2018.tar.gz 에서 장비 1대 + 고장 파일만 추출 (전체 해제 시 ~35GB)
tar -xzf ../data/phm_data_challenge_2018.tar.gz -C ../data 'phm_data_challenge_2018/train/train_faults' 'phm_data_challenge_2018/train/01_M01_DC_train.csv'
uv run python ingest_phm.py ../data/phm_data_challenge_2018/train/01_M01_DC_train.csv   # ~25초
uv run python index_docs.py                # knowledge/*.md → pgvector
uv run uvicorn main:app --port 8000        # API 문서: http://localhost:8000/docs
```
`OPENAI_API_KEY`는 셸 환경변수 또는 루트 `.env` (`.env.example` 참고). 키가 없으면 고정 순서 + 템플릿 보고서로 동작합니다.

확인:
- `uv run python tools.py` — 도구 셀프체크 (실데이터)
- `uv run python e2e_check.py` — 서버 실행 중: 요청 → SSE → 승인 전 저장 0건 → 수정 요청 → 승인 → 저장 1건, 작업자 승인 403

## 프론트엔드 (`frontend/`)

빌드 없는 정적 파일입니다. 로컬에서는 `python3 -m http.server -d frontend 5173` 후 http://localhost:5173 , 서버에서는 nginx가 `/`로 서빙하고 `/api`는 백엔드로 넘깁니다. 현재 화면은 목업 데이터이며 [docs/api.md](docs/api.md)로 연동합니다.

## 프로토타입 CLI (`src/etch_investigator/`)

과거 사례 JSON 샘플로 동작하는 초기 버전입니다. 조건이 부족하면 재질문하고, 유사 사례를 장비·챔버·레시피·제품·증상·계측 항목별 점수와 함께 찾아 z-score를 계산합니다.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
etch-investigate                                                   # 대화형
etch-investigate --question "ETCH-07 CH-B의 endpoint가 118초로 지연됐어"
etch-investigate examples/request_complete.json --output investigation_report.md   # 배치
PYTHONPATH=src python3 -m unittest discover -s tests -v            # 테스트
```

답변 후 승인용 조사 기록 작성 여부를 묻고, 작성하면 부족한 항목을 재질문한 뒤 검토·승인을 거쳐 `investigation_report.md`에 저장합니다. `InvestigationRepository`를 MES/FDC/APC, 정비 이력 DB, EDMS 검색으로 교체하면 그래프와 승인 흐름은 그대로 쓸 수 있습니다.

## 서버 배포 (EC2, docker compose)

외부 공개는 nginx `:80` 하나 (`/` 프론트, `/api/**` 백엔드). backend(8000)·postgres(5432)는 docker network 안에만 있습니다.
```bash
# 로컬: 공정 데이터 덤프
docker compose exec -T postgres pg_dump -U trace --data-only -Fc -t runs -t run_steps -t faults -t doc_chunks trace > trace_data.dump
rsync -az -e "ssh -i skala-key.pem" --exclude .venv --exclude __pycache__ backend frontend deploy docker-compose.prod.yml trace_data.dump ubuntu@<IP>:~/trace/
# 서버: ~/trace/.env 에 OPENAI_API_KEY, POSTGRES_PASSWORD (chmod 600)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T postgres pg_restore -U trace -d trace --data-only --disable-triggers < trace_data.dump
```
코드만 바뀌었으면 rsync 후 `up -d --build`만 다시 실행합니다.

참고: [LangGraph interrupts 공식 문서](https://docs.langchain.com/oss/python/langgraph/interrupts)
