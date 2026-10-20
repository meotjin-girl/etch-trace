# TRACE — 식각 공정 이상 조사 AI Agent (POC)

설계 문서: [docs/architecture.md](docs/architecture.md) (공유용 HTML은 `python3 docs/build_html.py`로 생성)

## 실행
```bash
docker compose up -d                       # PostgreSQL 16 + pgvector
cd agent && uv sync
# 데이터: data/phm_data_challenge_2018.tar.gz 에서 장비 1대 + 고장 파일만 추출 (전체 해제 시 ~35GB)
tar -xzf ../data/phm_data_challenge_2018.tar.gz -C ../data 'phm_data_challenge_2018/train/train_faults' 'phm_data_challenge_2018/train/01_M01_DC_train.csv'
uv run python ingest_phm.py ../data/phm_data_challenge_2018/train/01_M01_DC_train.csv   # ~25초
uv run python index_docs.py                # knowledge/*.md → pgvector
uv run uvicorn main:app --port 8000

cd ../frontend && npm install && npm run dev   # http://localhost:5173
```
`OPENAI_API_KEY`는 셸 환경변수 또는 루트 `.env` (`.env.example` 참고). 키가 없으면 고정 순서 + 템플릿 보고서로 동작합니다.

## 확인
- `uv run python tools.py` — 도구 셀프체크 (실데이터)
- `uv run python e2e_check.py` — 서버 실행 중: 요청 → SSE → 승인 전 저장 0건 → 수정 요청 → 승인 → 저장 1건, 작업자 승인 403

## 시연 순서
1. 작업자로 로그인 → "고장 기록 직전 run" 칩 선택 → 조사 요청
2. 엔지니어로 로그인 → 해당 조사 열기 → 타임라인(PLAN/TOOL)·근거 표·문서 근거 실시간 확인 → 수정 요청 → 재작성본 승인
3. 관리자로 로그인 → 승인 기록 INV-xxxx, 도구 호출 지표, 색인 문서 확인

## 서버 배포 (EC2, docker compose)
외부 공개는 nginx `:80` 하나. agent(8000)·postgres(5432)는 docker network 안에만 있음.
```bash
# 로컬: 프론트 빌드 + 공정 데이터 덤프
(cd frontend && npm run build)
docker compose exec -T postgres pg_dump -U trace --data-only -Fc -t runs -t run_steps -t faults -t doc_chunks trace > trace_data.dump
rsync -az -e "ssh -i skala-key.pem" --exclude .venv --exclude __pycache__ agent deploy docker-compose.prod.yml trace_data.dump ubuntu@<IP>:~/trace/
rsync -az -e "ssh -i skala-key.pem" frontend/dist ubuntu@<IP>:~/trace/frontend/
# 서버: ~/trace/.env 에 OPENAI_API_KEY, POSTGRES_PASSWORD (chmod 600)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T postgres pg_restore -U trace -d trace --data-only --disable-triggers < trace_data.dump
```
코드만 바뀌었으면 rsync 후 `up -d --build`만 다시 실행.
