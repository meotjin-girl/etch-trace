# TRACE v1.0.0

식각 공정 이상 질문을 접수하고, 부족한 정보를 재질문한 뒤 샘플 사례와 문서 조항으로 확인 가설을 작성합니다. 엔지니어는 수정 요청 또는 승인을 남깁니다. 승인은 물리적 원인의 확정이 아니라 **근거를 검토한 가설의 승인**입니다.

## 실행

저장소 루트의 `compose.yaml`이 유일한 서비스 구성입니다.

```bash
cp .env.example .env
# .env의 INTERNAL_API_KEY, POSTGRES_PASSWORD를 환경에 맞게 변경
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
```

`.env.example`의 `WEB_PORT=18080`을 사용하면 화면은 `http://localhost:18080`입니다. 기존 POC의 공개 포트와 겹치지 않도록 별도 포트를 사용합니다. `.env`를 생략하면 실제 기본 포트는 `compose.yaml`의 값을 따릅니다. backend, agent, MCP, PostgreSQL은 내부 네트워크에만 둡니다. nginx가 정적 화면과 `/api` 프록시를 제공합니다.

`seed`가 `db/cases.json`, `db/documents.json`을 PostgreSQL에 적재합니다. 이 데이터는 시연용 샘플이며 PHM 실측 데이터가 아닙니다. PHM 압축 해제, CSV 적재, 임베딩 색인, OpenAI 키는 v1 기본 실행의 필수 조건이 아닙니다. 현재 RAG MCP는 문서 ID를 정확히 조회하며 벡터 유사도 검색을 하지 않습니다.

## 단일 v1 구조

```text
브라우저 -> nginx -> business-mcp HTTP API -> backend 내부 이력 API -> DB (이력 조회)
              -> backend (REST / SSE, 작업·검토)
                         -> agent (유일한 LangGraph, PostgreSQL 체크포인트)
                              -> business-mcp -> backend 내부 사례 API
                              -> rag-mcp -> PostgreSQL 샘플 문서
```

| 경로 | 책임 |
|---|---|
| `frontend/` | backend API 연동 화면, 요청·재질문·검토·서버 이력 표시 |
| `backend/main.py`, `backend/v1_*.py` | 공개 API, 목업 신원, 권한, 상태·메시지·검토·이벤트·승인 스냅샷 |
| `agent/` | 질문 추출, 재질문, MCP 조사, 보고서, 검토 중단·재개 |
| `mcp/` | 사례 조회·결정론적 통계 계산, 문서 조항 조회 |
| `db/` | 샘플 사례·문서와 적재 스크립트 |
| `compose.yaml`, `deploy/` | 서비스 구성, nginx 프록시 |

숫자는 코드가 계산하며 단위와 근거 사례 ID를 보존합니다. 보고서는 `demo:true`이고 문서 ID·제목·본문, 누락 근거, 검토 의견을 포함합니다. 분류별 서브그래프나 담당 엔지니어 자동 배정은 v1 계약이 아닙니다.

## 요청과 검토

HTTP API에는 URL 인코딩한 `X-User-Name`과 `X-User-Role`이 **필수**입니다. 역할은 `worker`, `engineer`, `admin`입니다. 이는 검증된 인증이 아닌 개발용 신원입니다. 작업자는 자기 작업만, 엔지니어와 관리자는 전체 작업을 읽을 수 있습니다. 재질문 답변은 요청자만, 승인·수정은 엔지니어만 가능합니다.

```bash
curl -sS http://localhost:18080/api/ai/tasks \
  -H 'Content-Type: application/json' \
  -H 'X-User-Name: worker-demo' -H 'X-User-Role: worker' \
  -d '{"question":"ETCH-07 CH-B OX-120 endpoint 지연 118초, RF reflected power 상승 29W"}'
```

반환된 `taskId`로 상세·이력을 조회합니다. 정보가 부족하면 `WAITING_INPUT`에서 `/messages`에 `{text}`를 보냅니다. `WAITING_APPROVAL`에서는 엔지니어가 `/approval`에 `{action:"revise",comment:"..."}` 또는 `{action:"approve",comment:"..."}`를 보냅니다. 검토자 이름은 본문이 아니라 요청 신원에서 결정됩니다.

SSE는 `/api/ai/tasks/{id}/stream?user_name=worker-demo&user_role=worker&after=0`입니다. `EventSource`는 사용자 정의 헤더를 못 보내므로 목업 신원을 쿼리로 전달합니다. 이벤트 `seq`로 재연결·중복 제거하며 `DONE`, `INCOMPLETE`, `FAILED`에서 종료합니다. 목록에는 미완료 작업도 포함되고 상세에는 메시지·검토·이벤트·승인 스냅샷이 복원됩니다.

## 개발과 검증

루트 `pyproject.toml`은 개발 도구 메타데이터이며 설치할 CLI나 에이전트 런타임 패키지가 아닙니다. 서비스 의존성은 각 디렉터리가 소유합니다.

```bash
uv sync --group dev
(cd agent && uv sync --group dev && uv run pytest)
(cd backend && uv sync --group dev && uv run pytest)
uv run --project mcp python -m unittest discover -s tests -p 'test_evidence.py' -v
node --test frontend/frontend.test.mjs
```

위 명령은 실행 안내이며 통과 결과가 아닙니다. backend 테스트는 `TEST_DATABASE_URL`(기본 `postgresql:///postgres`)에 접속하여 격리 스키마를 만듭니다. agent의 실제 재시작 검증에는 `AGENT_TEST_DATABASE_URL`, evidence DB 검증에는 `EVIDENCE_TEST_DATABASE_URL`이 필요합니다. 테스트용 DB 계정에는 필요한 생성·정리 권한을 부여하고 운영 DB를 사용하지 마세요. 루트 개발 도구만 설치해도 서비스 의존성이 함께 설치되는 것은 아닙니다.

## 이전 구성에서 이동

- `docker-compose.yml`, `docker-compose.prod.yml`은 `compose.yaml`을 포함하는 호환 진입점입니다. Compose 2.20.3 이상을 사용하며, 각각 단독 `-f`로 실행합니다. wrapper와 원본을 여러 `-f`로 합치지 마세요. 별도 운영 아키텍처나 볼륨을 정의하지 않습니다.
- 기존 DB 볼륨을 v1 데이터로 간주하지 않습니다. v1은 `compose.yaml`의 `v1_pgdata`를 사용하고 샘플 데이터를 적재합니다. 기존 볼륨 삭제나 자동 마이그레이션은 수행하지 않습니다. 기존 POC와 병행할 때는 포트 외에 Compose 프로젝트 이름도 분리하세요.
- 이전 CLI 패키지, CLI JSON 입력 예제, CLI 전용 테스트는 제거했습니다. 질문·재질문·검토는 HTTP API를 사용합니다. 셸 입력, Markdown 파일 출력, 답변 후 기록 생성 여부 선택은 v1 기능이 아닙니다.
- 기존 브라우저 `localStorage` 기록은 **로컬 읽기 전용 과거 기록**입니다. 서버 승인 기록으로 이관하거나 새 조사 근거로 사용하지 않습니다.
- 중복 백엔드 그래프·도구와 PHM 전용 적재·점검 스크립트는 제거했습니다. 이전 구현은 Git 이력에서 확인할 수 있습니다.

Keycloak 인증과 승인된 조사 기록을 다음 조사의 근거로 검색하는 기능은 후속 범위입니다. 현재 이력 조회와 향후 근거 검색은 구분합니다.

문서: [목차](docs/README.md), [계약](docs/v1-contract.md), [API](docs/api.md), [에이전트](docs/agent.md), [아키텍처](docs/architecture.md).
