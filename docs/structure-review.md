# 구조 점검: 경로 지도와 수정 제안

기준: develop `d2be127`(PR #31 머지 시점). 2장의 세 가지 수정은 `feature/backend-integration`에서 반영했고, 공용 문서(`architecture.md`, `api.md`, `v1-contract.md`, `README.md`, `AGENTS.md`)도 같은 브랜치에서 갱신했다. 1장의 ⚠️·➕·➖는 수정 전 상태 기준 표기다.

backend는 FastAPI를 유지한다. 캡스톤 평가표(73쪽 표 6-14)에는 프레임워크 요구가 없고, 레퍼런스 아키텍처는 구성 요소별 역할과 금지 사항을 본다(52쪽 표 5-4: "평가에서는 금지 사항을 어긴 코드가 없는지 본다"). 현재 backend는 업무 서버 역할(업무 API, 작업 상태 저장, SSE 중계, 내부 API)을 하고 LLM을 호출하지 않는다.

표기: ⚠️ 문제, ➕ 추가 제안, ➖ 제거 제안. PDF 쪽수는 인쇄 쪽수(뷰어 페이지 번호는 +1).

## 1. 전체 경로 지도

### 공개 경로 (브라우저 → nginx `web`, 호스트 `WEB_PORT`)

| 경로 | 현재 | 제안 |
|---|---|---|
| `/`, `/records/*`, `/sop/*`, `/assets/*` | web 정적 `dist` + SPA fallback | 유지 |
| `/api/ai/investigations`, `/api/ai/investigations/{id}` | ⚠️ business-mcp:8000 직접 (PR #34) | ➖ nginx 블록 삭제 → `/api/` 규칙으로 backend 응답 |
| `/api/**` | backend:8000 (SSE 버퍼링 off) | 유지 |

### backend 공개 API (`X-User-Name` URL 인코딩, `X-User-Role`; SSE는 쿼리)

| 메서드·경로 | 호출자 | 상태 |
|---|---|---|
| `POST /api/ai/tasks` | 프론트 | 구현됨 |
| `GET /api/ai/tasks` | 프론트 | 구현됨 |
| `GET /api/ai/tasks/{id}` | 프론트 | 구현됨 |
| `POST /api/ai/tasks/{id}/messages` | 프론트 | 구현됨 |
| `POST /api/ai/tasks/{id}/approval` | 프론트 | 구현됨 |
| `GET /api/ai/tasks/{id}/events?after=` | 프론트 | 구현됨 |
| `GET /api/ai/tasks/{id}/stream?user_name&user_role&after` | 프론트(SSE) | 구현됨 |
| `GET /api/ai/investigations`, `/{id}` | (프론트 미사용) | ➕ backend에 추가, 기존 `Store.investigations` 재사용 |
| `GET /api/sops`, `/api/sops/{id}` | 프론트 SOP 화면 | ⚠️ 없음(404) → ➕ `sop-ocap/` 문서로 추가 |

### backend 내부 API (`X-Internal-Key`)

| 메서드·경로 | 호출자 | 용도 |
|---|---|---|
| `POST /internal/tasks/{id}/events` (+`X-Command-ID`) | agent | 진행·QUESTION·APPROVAL_REQUIRED·FAILED 콜백 |
| `POST /internal/tasks/{id}/investigation` (+`X-Command-ID`) | business-mcp `save_investigation` | DONE 저장(승인 스냅샷 검증) |
| `GET /internal/cases` | business-mcp `search_cases` | 데모 사례 |
| `GET /internal/investigations?user_name&user_role` | business-mcp `list_investigations` (⚠️ + `history_http`) | 승인 이력 목록 |
| `GET /internal/investigations/{id}?…` | business-mcp `get_investigation` (⚠️ + `history_http`) | 승인 이력 상세 |

### agent (agent:8000, 비공개)

| 경로 | 호출자 | 비고 |
|---|---|---|
| `POST /internal/tasks/{id}/run` | backend 디스패치 | `X-Internal-Key`, `X-Command-ID`, `X-Requester-Name`, `X-Requester-Role`. 그래프가 끝날 때까지 응답을 붙잡는 동기 호출(backend 타임아웃 30초) |

| 에이전트 노드 | MCP 도구 |
|---|---|
| 범위 조사 | business `search_cases`, `list_investigations`(요청자 신원) |
| 과거 Run 비교 | business `analyze_metrics` |
| 센서, 정비 | 없음(미연결) |
| 원인 후보·점검 추천 | rag `search_documents`, `search_sop` |
| 완료(DONE) | business `save_investigation` → backend `/internal/tasks/{id}/investigation` |
| (선택) | OpenAI, `OPENAI_API_KEY`가 있을 때만 |

### MCP 서버 (`/mcp`, 비공개)

| 서버 | 도구·경로 | 데이터 |
|---|---|---|
| business-mcp | `search_cases`, `analyze_metrics`, `save_investigation`, `list_investigations`, `get_investigation` | 모두 backend `/internal/**` 경유, DB 직접 접근 없음 |
| business-mcp | ⚠️ HTTP `GET /api/ai/investigations(/{id})` (`history_http`) | ➖ 삭제 제안 |
| rag-mcp | `search_documents(document_ids)` | postgres `etch_documents` |
| rag-mcp | `search_sop(query)` | sop-postgres(pgvector) + OpenAI 임베딩·재순위화, 문서 `/sop` |

### 파일·데이터 경로

| 경로 | 사용처 | 상태 |
|---|---|---|
| `sop-ocap/` (SOP 3종 + OCAP 19종) | 없음 | ⚠️ PR #31로 새로 생긴 실제 문서 위치 |
| `sop/` | rag-mcp 마운트(`./sop:/sop`), `tests/test_sop_retrieval.py` | ⚠️ 비어 있음 → ➕ `./sop-ocap`으로 변경 |
| `mcp/sop_chunks.py` | rag-mcp SOP 파서 | ⚠️ 새 머리 표를 못 읽고 `OCAP-` 파일 제외 → 수정 |
| `mcp/sop_questions*.json` | SOP 검색 평가셋 | ⚠️ 옛 문서 ID 기준, 작성자 확인 필요 |
| `db/cases.json`, `documents.json` → `etch_cases`, `etch_documents` | seed → `/internal/cases`, `search_documents` | 정상 |
| postgres `trace` `v1_*` | backend 전용 | 정상 |
| postgres `trace` LangGraph 체크포인트 | agent 전용 | 정상 |
| sop-postgres `trace_sop` | rag-mcp 전용 | 정상 |

## 2. 문제와 변경안

### 2.1 SOP RAG가 실제 문서를 찾지 못한다

- PR #31이 문서를 `sop/`에서 `sop-ocap/`으로 옮겼지만 `compose.yaml` rag-mcp는 빈 `./sop`를 마운트한다.
- 경로만 바꿔도 실패한다.
  - `mcp/sop_chunks.py`의 개정 정규식 `^\| 개정 \| (.+?) \|$`는 새 머리 표(`| 담당 팀 | 버전 | 최근 개정 |` 다음 행에 값)와 맞지 않아 모든 문서가 `Missing revision`으로 거부된다.
  - `load_chunks`의 접두사 필터(`SOP-`, `WI-`, `SPEC-`)가 `OCAP-` 19종을 제외한다.
- 테스트도 현재 실패한다(`uv run --project mcp --group rag-experiment python -m unittest discover -s tests -p 'test_sop_*.py'`, 2026-10-21 확인: 20개 중 3개 오류, 5개는 DB 미설정으로 건너뜀). 3개 모두 `No SOP sections found: …/sop`다.
  - `test_sop_retrieval.ChunkTest.test_real_corpus_preserves_existing_document_ids`
  - `test_sop_retrieval.ChunkTest.test_evaluation_ids_exist_and_categories_have_planned_counts`
  - `test_sop_rerank.RerankTest.test_additional_questions_reference_real_sections`
  - 뒤의 두 테스트는 평가셋(`mcp/sop_questions*.json`)의 문서 ID가 실제 문서에 있는지 검사한다. 경로를 고쳐도 평가셋을 `sop-ocap/` 기준으로 갱신하기 전까지는 실패한다.
  - 첫 테스트는 옛 문서 기준 단언이다. 문서 7개, `db/documents.json`의 조항 ID 5개(`WI-`, `SPEC-` 문서 포함) 존재, 모든 조각의 `> ` 안내문을 검사한다. 새 `sop-ocap/` 문서는 22개이고 `WI-`·`SPEC-` 문서와 안내문 줄이 없다.
- 수정 후(이 브랜치): 파서·로더 테스트는 통과한다(새 머리 표 테스트 추가, 21개 중 실패 3·건너뜀 5). 남은 3개 실패는 모두 위 데이터 내용 단언이다. 평가셋·`db/documents.json`·안내문 정책은 SOP 실험·문서 작성자가 정하도록 그대로 둔다(결정: 그대로 두고 PR에 명시).
- 변경안
  - 파서가 새 머리 표에서 `버전`·`최근 개정`을 읽는다(옛 `| 개정 |` 행도 유지).
  - 접두사에 `OCAP-`를 추가한다.
  - rag-mcp 볼륨을 `./sop-ocap:/sop:ro`로 바꾼다.
  - 테스트 경로를 `sop-ocap`으로 고친다.
- 영향: 추천 에이전트의 `search_sop`가 22개 문서의 절 단위 조항을 반환한다(`OPENAI_API_KEY` 필요). `README.md`, `00_` 메모는 제외된다.

### 2.2 이력 조회의 공개 요청이 MCP에 닿는다

```
① 이전 (v1_history)   Vue → nginx → Backend → business-mcp → Backend(/internal) → DB   ← 왕복
② 현재 (PR #34)       Vue → nginx → business-mcp → Backend(/internal) → DB              ← 공개 요청이 MCP로
③ 제안                Vue → nginx → Backend → DB                                         ← 화면 조회는 MCP 없이
   (에이전트용)       Agent → business-mcp(list_investigations) → Backend(/internal) → DB  ← 유지
```

- ②는 ①의 왕복을 없애려는 의도였다. 왕복의 원인은 화면 조회 경로에 MCP가 끼어 있다는 점이고, ②에도 `MCP → Backend /internal`이 남는다. 완전히 없애려면 ③처럼 backend가 이미 가진 `Store.investigations(actor)`로 바로 응답한다.
- PDF 근거
  - 47쪽 표 5-1: "공개 포트는 화면과 Spring Boot뿐", "business mcp는 DB에 직접 접근하지 않고 … /internal/** 를 호출한다"
  - 50쪽 그림 5-2: "공개 포트는 Spring Boot와 화면뿐"
  - 51쪽 표 5-3: Vue → 업무 서버, business mcp → 업무 서버 `/internal/**` 흐름만 있다. 브라우저 → MCP 흐름은 없다
  - 52쪽 표 5-4: business mcp는 "업무 기능을 Agent가 호출하는 도구로 노출", 금지 사항 "업무 규칙 복제". `history_http`는 신원 검사·오류 매핑을 다시 구현한다
  - 55쪽 표 5-6, 66쪽 표 5-12(Trust Boundary: "공개 포트는 frontend와 backend뿐")
  - 73쪽 표 6-14: MCP 점수는 "Agent가 연결해 호출함"
  - 단, "nginx로 MCP에 연결하면 안 된다"는 문장이 직접 있지는 않다. 위 원칙을 종합한 해석이다
- 변경안
  - backend에 `GET /api/ai/investigations`, `/{id}`를 추가한다.
  - nginx의 investigations 블록을 지운다.
  - business-mcp `history_http`를 지운다(도구 5개는 유지).
  - web의 `depends_on: business-mcp`를 지운다.
  - `tests/test_history_http.py`의 시나리오를 backend 테스트로 옮긴다.
- 영향: 응답 형식(`InvestigationRecord`)과 권한 규칙은 같다. 프론트는 이 API를 아직 쓰지 않는다.

### 2.3 프론트 SOP 화면이 404를 받는다

- 프론트는 `GET /api/sops`, `/api/sops/{id}`를 호출하지만 backend에 없다(`docs/frontend.md` 필요 API 8·9번).
- 변경안
  - backend가 `SOP_DOCUMENTS_DIR`(compose에서 `./sop-ocap:/sop:ro`)의 `SOP-*`, `OCAP-*` 문서를 읽어 응답한다.
  - 필드는 첫 줄 `# <ID> <제목>`, 머리 표(담당 팀·버전·최근 개정), 첫 문단 설명, 분류(`SOP`/`OCAP`), 원문 `markdown`, `demo: true`다.
- 영향: SOP 화면에 22개 문서가 표시된다.

## 3. 그대로 두는 것

- agent 전체: 노드, MCP 호출, `/internal/tasks/{id}/run`
- MCP 도구 5개
- backend 기존 API 13개와 DB 스키마
- 프론트 코드
- `db/documents.json`의 시연용 조항 5건: 사례 데이터와 연결돼 있어 이번 범위에서 제외

## 4. 작성자에게 확인할 점

- PR #31(SOP·OCAP 문서): `sop-ocap/` 머리 표 형식을 RAG 파서와 SOP 화면의 기준 형식으로 삼아도 되는지
- PR #34(이력 조회): ③(backend 직접 응답)으로 되돌리는 데 다른 이유(예: 시연에서 MCP 경유를 보여 주려는 의도)가 있었는지
- SOP 검색 실험: `mcp/sop_questions*.json`의 기대 정답을 `sop-ocap/` 문서 기준으로 다시 정해 줄 수 있는지
