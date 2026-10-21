# TRACE v1.0.0

식각 공정 이상 질문을 접수하고, 부족한 정보를 재질문한 뒤 샘플 사례와 문서 조항으로 확인 가설을 작성합니다. 로그인한 팀원은 공동으로 답변·수정 요청·승인을 남깁니다. 승인은 물리적 원인의 확정이 아니라 **근거를 검토한 가설의 승인**입니다.

## 실행

저장소 루트의 `compose.yaml`이 유일한 서비스 구성입니다.

```bash
cp .env.example .env
# .env의 INTERNAL_API_KEY, POSTGRES_PASSWORD, KEYCLOAK_ADMIN_PASSWORD 변경
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
```

`.env.example`의 `WEB_PORT=18080`을 사용하면 화면은 `http://localhost:18080`입니다. 기존 POC의 공개 포트와 겹치지 않도록 별도 포트를 사용합니다. `.env`를 생략하면 실제 기본 포트는 `compose.yaml`의 값을 따릅니다. backend, agent, MCP, PostgreSQL은 내부 네트워크에만 둡니다. nginx가 정적 화면과 `/api` 프록시를 제공합니다.

새 환경에서는 기본 계정 **`test` / `test`**로 바로 로그인할 수 있습니다. Keycloak 관리자 화면은 같은 주소의 `/auth/admin/`이며, 추가 계정은 관리자가 `trace` realm에 만듭니다. 회원가입은 제공하지 않습니다. 기존 볼륨의 기본 계정 추가 방법은 [계정 생성·URL·영속성 안내](deploy/keycloak/README.md)를 참고하세요.

`seed`가 `db/cases.json`, `db/documents.json`을 PostgreSQL에 적재합니다. 이 데이터는 시연용 샘플이며 PHM 실측 데이터가 아닙니다. PHM 압축 해제, CSV 적재, 임베딩 색인, OpenAI 키는 v1 기본 실행의 필수 조건이 아닙니다. RAG MCP는 문서 ID 정확 조회(`search_documents`)와 `sop-ocap/` SOP·OCAP 문서의 의미 검색(`search_sop`, sop-postgres pgvector)을 제공합니다. 의미 검색에는 `OPENAI_API_KEY`가 필요하며 키가 없으면 보고서에 조회 실패로 표시됩니다.

## 단일 v1 구조

```text
브라우저(Vue 3) -> nginx(dist 서빙) -> backend (REST / SSE, 작업·판별·승인 이력·SOP)
                                          -> agent (유일한 LangGraph, 조사 에이전트 5개, PostgreSQL 체크포인트)
                                               -> business-mcp -> backend 내부 사례·이력·승인 저장 API
                                               -> rag-mcp -> PostgreSQL 샘플 문서 / sop-postgres SOP·OCAP 색인
```

| 경로 | 책임 |
|---|---|
| `frontend/` | Vue 3 + TypeScript 화면(Vite). 질문·재질문·채팅 판별·조사 기록·SOP. [docs/development/frontend.md](docs/development/frontend.md) |
| `backend/main.py`, `backend/v1_*.py` | 공개 API, JWT 검증·공동 작업 인가, 상태·메시지·검토·이벤트·승인 스냅샷 |
| `agent/` | 질문 추출, 재질문, MCP 조사, 보고서, 검토 중단·재개 |
| `mcp/` | 사례 조회·결정론적 통계·승인 이력 도구, 문서 조항 조회·SOP 의미 검색 |
| `sop-ocap/` | SOP 3종·OCAP 19종 원문. SOP 화면과 SOP 의미 검색의 출처 |
| `db/` | 샘플 사례·문서와 적재 스크립트 |
| `compose.yaml`, `deploy/` | 서비스 구성, nginx 프록시 |

숫자는 코드가 계산하며 단위와 근거 사례 ID를 보존합니다. 보고서는 `demo:true`이고 문서 ID·제목·본문, 누락 근거, 검토 의견을 포함합니다. 분류별 서브그래프나 담당 엔지니어 자동 배정은 v1 계약이 아닙니다.

## 요청과 검토

공개 데이터 API는 `Authorization: Bearer <access token>`이 필수입니다. backend가 Keycloak 서명·issuer·audience·만료를 검증합니다. 로그인한 사용자는 모두 조회·추가 답변·검토할 수 있고, 역할·소유자별 제한은 후속 범위입니다. 토큰은 브라우저 메모리에만 보관합니다.

```bash
curl -sS http://localhost:18080/api/ai/tasks \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TRACE_ACCESS_TOKEN" \
  -d '{"question":"ETCH-07 CH-B OX-120 endpoint 지연 118초, RF reflected power 상승 29W"}'
```

반환된 `taskId`로 상세·이력을 조회합니다. 정보가 부족하면 `WAITING_INPUT`에서 `/messages`에 `{text}`를 보냅니다. `WAITING_APPROVAL`에서는 `/approval`에 `{action:"revise",comment:"..."}` 또는 `{action:"approve",comment:"..."}`를 보냅니다. 검토자 신원은 본문이 아니라 검증된 토큰에서 결정됩니다.

SSE는 `/api/ai/tasks/{id}/stream?after=0`에 Bearer 헤더를 보내는 fetch 스트림입니다. 이벤트 `seq`로 복원·중복 제거하고, 토큰 만료로 닫히면 갱신된 토큰으로 이어받습니다. `DONE`, `INCOMPLETE`, `FAILED`에서 종료합니다. 목록에는 미완료 작업도 포함되고 상세에는 메시지·검토·이벤트·승인 스냅샷이 복원됩니다.

## 개발과 검증

루트 `pyproject.toml`은 개발 도구 메타데이터이며 설치할 CLI나 에이전트 런타임 패키지가 아닙니다. 서비스 의존성은 각 디렉터리가 소유합니다.

```bash
uv sync --group dev
(cd agent && uv sync --group dev && uv run pytest)
(cd backend && uv sync --group dev && uv run pytest)
uv run --project mcp python -m unittest discover -s tests -p 'test_evidence.py' -v
(cd frontend && npm ci && npm run type-check && npm test)   # npm run dev:mock 으로 backend 없이 화면 확인
uv run --project mcp --group rag-experiment python -m unittest discover -s tests -p 'test_sop_*.py' -v
```

위 명령은 실행 안내이며 통과 결과가 아닙니다. backend 테스트는 `TEST_DATABASE_URL`(기본 `postgresql:///postgres`)에 접속하여 격리 스키마를 만듭니다. agent의 실제 재시작 검증에는 `AGENT_TEST_DATABASE_URL`, evidence DB 검증에는 `EVIDENCE_TEST_DATABASE_URL`이 필요합니다. 테스트용 DB 계정에는 필요한 생성·정리 권한을 부여하고 운영 DB를 사용하지 마세요. 루트 개발 도구만 설치해도 서비스 의존성이 함께 설치되는 것은 아닙니다.

## 이전 구성에서 이동

- `docker-compose.yml`, `docker-compose.prod.yml`은 `compose.yaml`을 포함하는 호환 진입점입니다. Compose 2.20.3 이상을 사용하며, 각각 단독 `-f`로 실행합니다. wrapper와 원본을 여러 `-f`로 합치지 마세요. 별도 운영 아키텍처나 볼륨을 정의하지 않습니다.
- 기존 DB 볼륨을 v1 데이터로 간주하지 않습니다. v1은 `compose.yaml`의 `v1_pgdata`를 사용하고 샘플 데이터를 적재합니다. 기존 볼륨 삭제나 자동 마이그레이션은 수행하지 않습니다. 기존 POC와 병행할 때는 포트 외에 Compose 프로젝트 이름도 분리하세요.
- 이전 CLI 패키지, CLI JSON 입력 예제, CLI 전용 테스트는 제거했습니다. 질문·재질문·검토는 HTTP API를 사용합니다. 셸 입력, Markdown 파일 출력, 답변 후 기록 생성 여부 선택은 v1 기능이 아닙니다.
- 기존 브라우저 `localStorage` 기록은 **로컬 읽기 전용 과거 기록**입니다. 서버 승인 기록으로 이관하거나 새 조사 근거로 사용하지 않습니다.
- 중복 백엔드 그래프·도구와 PHM 전용 적재·점검 스크립트는 제거했습니다. 이전 구현은 Git 이력에서 확인할 수 있습니다.

Keycloak은 개발용 Compose 서비스로 포함합니다. 설정은 [Keycloak 안내](deploy/keycloak/README.md)를 참고하세요.

문서: [개발 목차](docs/development/README.md), [기획 보고서](docs/planning/final.md), [계약](docs/development/v1-contract.md), [API](docs/development/api.md), [에이전트](docs/development/agent.md), [아키텍처](docs/development/architecture.md).
