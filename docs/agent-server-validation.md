# Agent Server 실행 검증

2026-10-23, `e275c3a` 기준 작업 트리 변경을 실제 개발 스택에서 확인했다.
비밀 값과 access token은 증거에 기록하지 않았다. Git commit은 만들지 않았다.

## 현재 접속

- 웹: `http://localhost:18081`
- Agent Server: `http://localhost:12024`
- Studio: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:12024`
- 그래프: `trace` (`investigator`는 동일 그래프 별칭)

개발 스택은 실험을 이어갈 수 있도록 실행 상태로 유지한다.
Compose 프로젝트는 `etchtrace-agentnew-qa`다. 별도 시험 DB와 브라우저는 종료했다.
18080은 다른 프로젝트가 사용 중이어서 변경하지 않았다.

Studio의 localhost 연결에는 `X-Auth-Scheme: custom`과 `.env`의 내부 키를
Custom Headers로 설정한다. 공개 웹 `/agent/`는 이 두 헤더를 제거하고
Keycloak 토큰을 검증한다.

후속 Aside 실브라우저 검증에서 초기 `Forbidden`을 재현하고 수정했다.
Studio가 헤더를 `langsmith, custom`으로 합치며 자체 Bearer도 보내는 것이
원인이었다. 명시적 custom 모드와 검증된 로컬 키를 함께 처리하도록 수정했다.
그 뒤 실제 `trace` 그래프의 prepare·agent·tools·reason·publish가 표시되고,
Chat에서 “안녕하세요. 식각 이상 조사를 어떻게 시작하면 되나요?”에 대한
실제 모델 답변을 확인했다. 인증 회귀 19개와 정적 검사도 통과했다.
상세 진단 기록은 `.omo/evidence/agent-server/studio-auth-fix.md`에 있다.

## 실제 모델·서비스 결과

```bash
TRACE_URL=http://localhost:18081 \
TRACE_THREAD_ID=00000000-0000-4000-8000-000000002304 \
uv run --project backend --env-file .env node tests/check_agent_server.mjs

uv run --project backend --env-file .env node tests/check_studio.mjs
```

모두 PASS:

- 실제 Keycloak authorization-code PKCE 로그인
- 경보로 thread 생성, 초기 후보 저장 전 backend 조사 없음
- OpenAI와 MCP 근거 조회를 통한 초기 분석 및 후보 저장
- 같은 조사 ID에서 후속 분석: revision 1 → 2, 별도 조사 생성 안 함
- backend가 검증한 사용자로 후보 승인, 후보 사본 보관
- 승인 후 같은 thread 대화 지속, 승인 사본 유지
- nginx 공개 경로의 인증 및 임의 state 수정 차단
- Studio의 기본 assistant 조회와 그래프·입력 스키마 조회

실행 증거: `.omo/evidence/agent-server/http-qa.json`,
`studio-api.json`. 내부 키와 토큰은 저장하지 않는다.

## 웹 정상 경로

독립 브라우저에서 개발 계정 `test`로 로그인했다. 목록 첫 화면, 실제 원인 후보와
승인 사본 표시, 승인된 조사에서 추가 질문과 실제 모델 답변을 확인했다.
데스크톱 1440과 모바일 CSS 390에서 캡처를 직접 확인했다.
Studio 연결과 정상 대화 우선 범위로 UI의 모든 예외·경쟁 상황을 확장 시험하지 않았다.
승인 버튼의 클릭 흐름을 별도로 반복하지 않았으며 승인 저장은 실제 HTTP로 검증했다.

증거:

- `.omo/evidence/agent-server/list-empty-desktop.png`
- `.omo/evidence/agent-server/list-empty-phone.png`
- `.omo/evidence/agent-server/detail-desktop.png`
- `.omo/evidence/agent-server/chat-after-approval-desktop.png`
- `.omo/evidence/agent-server/chat-after-approval-phone.png`

## 테스트와 정적 검사

| 범위 | 결과 |
|---|---|
| backend 전체 실제 PostgreSQL/HTTP 테스트 | 134 통과 |
| agent-new 그래프·체크포인트·MCP·인증 | 37 통과 |
| frontend Vitest | 62 통과 |
| frontend type-check / production build | 통과 |
| 기존 agent | 8 통과 |
| MCP evidence / physics / live business | 26 통과 |
| SOP retrieval / rerank | 19 통과, 기존 corpus 기대 불일치 3 실패 |
| 변경 Python의 서비스별 Ruff / basedpyright | 통과 |
| 실제 nginx 이미지 구문 검사 / 최종 Compose health | 통과 |

backend와 agent-new는 자체 개발 의존성으로 pytest·Ruff·basedpyright를 실행했다.
frontend는 `npm run type-check && npm test && npm run build`로 확인했다.
MCP는 `uv run --project mcp` 환경에서 실행했다.
워크스페이스 LSP가 서비스별 venv를 찾지 못하는 진단은 서비스 CLI 검사로 확인했다.
Vite 및 Authlib의 upstream 경고는 숨기지 않았다.

SOP의 기존 실패:

- `ChunkTest.test_real_corpus_preserves_existing_document_ids`: 기대 7개, 현재 22개
- `ChunkTest.test_evaluation_ids_exist_and_categories_have_planned_counts`
- `RerankTest.test_additional_questions_reference_real_sections`

위 기대 불일치는 수정 전후 동일하다. corpus와 평가 문항을 이 작업에서
바꾸거나 테스트를 삭제·완화하지 않았다.

## 실행에서 발견해 수정한 것

- nginx `rewrite ... break` 뒤의 upstream 변수 설정이 실행되지 않던 문제
- 병렬 최초 SOP 검색의 확장·색인 초기화 경쟁: PostgreSQL transaction advisory lock 적용
- 모델이 새 후보 UUID를 임의 생성하던 문제: 구조화 출력 ID를 기존 ID와 null로 제한
- 새 목록 빈 상태의 한국어 단어 줄바꿈

SOP 잠금 회귀 시험은 실제 PostgreSQL에서 확인했다. 잠금을 제거하면 새 시험이
실패하고 복원하면 통과하는 것도 확인했다. 고정 sleep으로 테스트를 동기화하지 않았다.

## 자체 검토와 범위

새 모듈·인증·DB·외부 연동을 포함하므로 HEAVY 분류를 유지했다.
단일 ReAct 루프와 필수 업무 저장 단계가 분리됐고, 대화 state와 승인 사본의
소유권이 나뉜다. 기존 v1 경로와 agent는 보존했다.
별도 ulw-plan은 작성하지 않아 plan-gated reviewer는 실행하지 않았다.

동일 경보 중복 방지, 저장 실패 복구, 재승인·승인 취소,
프로덕션 Agent Server 배포와 기존 대화 자동 이관은 이번 범위가 아니다.
