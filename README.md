# TRACE v1.0.0

식각 장비 경보를 받아 원인 후보를 조사하고, 초기 분석을 조사 목록에 공개합니다.
로그인한 팀원은 같은 조사에서 질문을 이어가고 후보를 보완·선택·승인합니다.
승인 후에도 대화할 수 있으며, 승인은 물리적 원인의 확정이 아니라
**근거를 검토한 가설의 승인**입니다.

신규 실행 구조와 실험 방법은 [Agent Server 안내](docs/agent-server.md)를 참고하세요.
기존 v1 task API는 호환 경로로 보존합니다.

## 실행

저장소 루트의 `compose.yaml`이 유일한 서비스 구성입니다.

```bash
cp .env.example .env
# .env의 OPENAI_API_KEY, OPENAI_MODEL 설정 및 내부 키·개발 비밀번호 변경
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
```

`.env.example`의 `WEB_PORT=18080`을 사용하면 화면은 `http://localhost:18080`입니다.
다른 실행과 겹치면 포트와 Compose 프로젝트명을 분리하세요.
nginx가 정적 화면과 `/api`, `/agent`, `/auth` 경로를 나눠 제공합니다.
Agent Server의 Studio용 포트는 localhost의 2024로 공개합니다.
backend, MCP, PostgreSQL은 내부 네트워크에 둡니다.

새 환경에서는 기본 계정 **`test` / `test`**로 바로 로그인할 수 있습니다. Keycloak 관리자 화면은 같은 주소의 `/auth/admin/`이며, 추가 계정은 관리자가 `trace` realm에 만듭니다. 회원가입은 제공하지 않습니다. 기존 볼륨의 기본 계정 추가 방법은 [계정 생성·URL·영속성 안내](deploy/keycloak/README.md)를 참고하세요.

`seed`가 `db/cases.json`, `db/documents.json`을 PostgreSQL에 적재합니다.
이 데이터는 시연용 샘플이며 PHM 실측 데이터가 아닙니다.
새 Agent의 실제 분석에는 `OPENAI_API_KEY`가 필요합니다.
RAG MCP는 문서 ID 정확 조회와 `sop-ocap/` SOP·OCAP 의미 검색을 제공합니다.

## 실행 구조

```text
브라우저(Vue 3) -> nginx -> backend (조사 목록·현재 후보·승인·SOP)
                       -> agent-new (Agent Server, thread·대화·실행)
                            -> business-mcp -> backend 조사 저장·사례 API
                            -> rag-mcp -> 문서 / SOP·OCAP 색인
                            -> physics-mcp -> 결정론적 식각 관계식 계산
```

| 경로 | 책임 |
|---|---|
| `frontend/` | Vue 3 + TypeScript 화면(Vite). 질문·재질문·채팅 판별·조사 기록·SOP. [docs/frontend.md](docs/frontend.md) |
| `backend/main.py`, `backend/v1_*.py` | 공개 API, JWT 검증·공동 작업 인가, 상태·메시지·검토·이벤트·승인 스냅샷 |
| `agent-new/` | 표준 Agent Server 진입점, 단일 ReAct 조사, 구조화 후보·필수 업무 저장 |
| `agent/` | 이전 단일 ReAct 구현과 회귀 테스트; `legacy` profile로 실행 |
| `mcp/` | 사례 조회·결정론적 통계·승인 이력 도구, 문서 조항 조회·SOP 의미 검색 |
| `mcp/physics_models.py`, `mcp/physics.py` | 식각 깊이·평균 식각 속도·선택비 계산과 입력 검증. [Physics v1](docs/physics.md) |
| `sop-ocap/` | SOP 3종·OCAP 19종 원문. SOP 화면과 SOP 의미 검색의 출처 |
| `db/` | 샘플 사례·문서와 적재 스크립트 |
| `compose.yaml`, `deploy/` | 서비스 구성, nginx 프록시 |

숫자는 코드가 계산하며 단위와 근거 사례 ID를 보존합니다. 보고서는 `demo:true`이고 문서 ID·제목·본문, 누락 근거, 검토 의견을 포함합니다. 분류별 서브그래프나 담당 엔지니어 자동 배정은 v1 계약이 아닙니다.

## 신규 조사와 대화

로그인 후 첫 화면은 `/api/investigations`의 조사 목록입니다. 경보로 시작한
thread에서 초기 후보 제안과 Business MCP 저장이 끝나면 목록에 나타납니다.
조사 ID와 thread ID는 동일한 UUID이며 후속 분석이 별도 조사를 만들지 않습니다.
대화는 `/agent/threads/{id}/state`와 run API로 조회·실행하고, 업무 상세와
후보 승인 정보는 backend에서 조회합니다. 현재 후보는 갱신되지만 승인 당시
선택한 후보 사본은 보존됩니다.

## 기존 v1 요청과 검토 (호환 경로)

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
(cd agent-new && uv sync --group dev && uv run pytest)
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

Keycloak은 개발용 Compose 서비스로 포함합니다. 실제 검증 범위는 [인증 이식 검증 기록](docs/keycloak-validation.md)을 참고하세요.

문서: [목차](docs/README.md), [계약](docs/v1-contract.md), [API](docs/api.md), [에이전트](docs/agent.md), [아키텍처](docs/architecture.md).
