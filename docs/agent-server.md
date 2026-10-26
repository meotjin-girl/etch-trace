# Agent Server 실험 환경

## 실행

루트 `.env`의 `OPENAI_API_KEY`, `OPENAI_MODEL`, `INTERNAL_API_KEY`를 설정한다.
키를 Git에 추가하지 않는다.

```bash
docker compose -f compose.yaml up -d --build
```

기본 `.env.example`의 웹 포트는 18080이다. 다른 서비스가 사용한다면 다음처럼
포트와 Keycloak 공개 주소를 함께 지정한다.

```bash
WEB_PORT=18081 KEYCLOAK_URL=http://localhost:18081/auth \
WEB_ORIGIN=http://localhost:18081 AGENT_SERVER_PORT=12024 \
docker compose -p trace-experiment -f compose.yaml up -d --build
```

웹 로그인은 새 개발 realm의 `test` / `test` 계정을 사용한다.
기존 `agent/`는 참조·레거시용으로 보존하며 기본 실행은 `agent/`다.
레거시 컨테이너는 `--profile legacy`로 추가 실행할 수 있다.

## 데이터 책임

```text
Emitter → Agent Server thread/run → 근거 조회·원인 후보 생성
                                  → Business MCP → backend 조사 신규 저장

Web → /api/investigations → 조사 목록·현재 후보·승인
Web → /agent/threads/…    → 대화 조회·추가 질문·실행 스트림
```

조사 ID는 thread UUID와 같다. 초기 제안이 생성된 뒤에만 목록에 나타난다.
후속 질문에서 후보가 바뀌면 같은 조사 행의 현재 후보 목록을 교체한다.
후보마다 UUID가 있어 화면의 순서가 바뀌어도 선택 대상을 식별할 수 있다.
승인 시 backend가 검증한 사용자와 선택 후보의 사본을 기록한다.
승인 후 대화와 후보 보완은 계속 가능하며, 승인 당시 사본은 변경하지 않는다.

기존 `/api/ai/*`의 작업·이벤트·승인된 이력 API는 호환 경로로 남는다.
새 화면은 이 경로의 `WAITING_INPUT`·`WAITING_APPROVAL` 조건을 사용하지 않는다.

## API와 저장 시점

| 호출 | 용도 |
|---|---|
| `POST /threads` | Emitter가 Agent Server에 thread 생성 |
| `POST /threads/{id}/runs` | `trace` 그래프로 초기 경보 조사 시작 |
| `GET /agent/threads/{id}/state` | 웹이 같은 thread의 대화 복원 |
| `POST /agent/threads/{id}/runs/stream` | 웹이 후속 질문 실행, `values` 스트림 수신 |
| `GET /api/investigations` | 초기 후보가 저장된 조사 목록 |
| `GET /api/investigations/{id}` | 요약·현재 후보·원본 경보·승인 사본 |
| `POST /api/investigations/{id}/approval` | 현재 후보 선택·승인 |
| `DELETE /api/investigations/{id}/approval` | 원인 선택 취소(재선택용) 204. 승인이 없거나 조치가 이미 기록됐으면 409 |
| `POST /api/investigations/{id}/action` | 승인 후 현장 조치 기록 `{content,result}` 1회. 승인 전·중복은 409, 기록자는 검증된 `sub` |

graph 입력은 다음 봉투를 사용한다. 경보의 `system`은 출처를 구분하는
필드이며 LLM system 지시문으로 전달하지 않는다.

```json
{
  "assistant_id": "trace",
  "input": {
    "request": {
      "role": "system",
      "content": "[경보] ETCH-02 / CH-A / Lot DEMO-LOT / Wafer W01 / RCP-OX-ETCH-EDU-01\n- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W (한계 37 W) (OCAP-ETCH-RF)"
    }
  },
  "multitask_strategy": "reject"
}
```

웹의 후속 질문은 같은 thread에서 `role:"user"`와 질문 내용을 전달한다.
이미 진행 중인 run은 새로 생성하지 않고 조회 후 기존 스트림에 연결한다.

Agent의 `publish` 노드는 최초 후보 생성 후 `upsert_live_investigation`을
반드시 호출한다. 이후 변경 없는 대화는 업무 저장을 생략하며, 후보 변경은
현재 목록 전체를 같은 조사 ID에 저장한다. Business MCP는 backend의
`PUT /internal/investigations/live/{thread_id}`를 호출한다.

승인 본문은 `candidate_id`, `expected_revision`, `comment`다.
본문에 사용자 이름·ID·승인 시각을 넣지 않는다. backend가 현재 revision과
후보를 잠금 안에서 검증하고 토큰의 사용자를 기록한다. revision은 동일 조사
내의 갱신 번호이지 새 조사 ID가 아니다. 재승인과 승인 취소는 이번 범위가 아니다.

## 인증과 nginx

웹의 기존 Keycloak PKCE 로그인과 메모리 access token을 재사용한다.
nginx는 `/api/`를 backend로, `/agent/`의 대화 경로를 Agent Server로 보낸다.
양쪽 서비스가 access JWT의 issuer, audience, 만료와 서명을 검증한다.
로그인 사용자들은 같은 조사를 함께 읽고 대화하고 승인할 수 있다.
nginx 라우팅 자체가 인증을 대신하지 않는다.

Emitter는 서버 간 내부 키로 Agent Server를 호출한다. nginx 공개 경로에서는
내부 키와 LangSmith 인증 우회 헤더를 제거한다. thread 삭제와 임의 state
수정 API는 공개하지 않는다.

## Studio와 저장소

`agent/langgraph.json`의 `trace` 그래프를 사용한다. 개발용 서버 주소는
기본적으로 `http://localhost:2024`이고 위 포트 변경 예에서는 12024다.
LangSmith 로그인과 로컬 Agent Server 인증은 별개다. Studio의
**Server connection settings → Custom Headers**에 다음 두 항목을 설정한다.

| Header | 값 |
|---|---|
| `X-Auth-Scheme` | `custom` |
| `X-Internal-Key` | 루트 `.env`의 `INTERNAL_API_KEY` |

이 값은 해당 브라우저의 로컬 연결 설정에 저장된다. 개발 장비에서만 사용하고,
키를 문서·스크린샷·Git에 포함하지 않는다. Studio는 자체 LangSmith Bearer도
보내므로, 명시적 custom 모드와 검증된 내부 키가 있을 때 로컬 Studio 신원으로
인증한다. 잘못된 Bearer만 보낸 일반 요청은 계속 거부한다.
nginx의 웹 `/agent/`는 위 두 헤더를 제거하고 Keycloak Bearer를 검증한다.

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:12024
```

위 포트 변경 예를 사용한 주소다. 기본 포트로 실행했다면 2024로 바꾼다.
그래프는 `trace`를 선택한다. 초기 경보는 Graph 모드의 `request`에
`{"role":"system","content":"경보 원문"}`을 입력한다.
후속 대화는 같은 thread에서 `{"role":"user","content":"추가 질문"}`으로 실행한다.
Chat 모드의 일반 messages 입력도 지원한다.

Studio의 **Input → View Raw**에는 HTTP run 본문이 아니라 graph 입력만 넣는다.
아래는 교육용 합성 경보 예시다.

```json
{
  "request": {
    "role": "system",
    "content": "[경보] ETCH-01 / CH-A / Lot DEMO-LOT-001 / Wafer W01 / RCP-OX-ETCH-EDU-01\n- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W (한계 37 W) (OCAP-ETCH-RF)"
  }
}
```

일반 입력 폼의 content에는 바깥 따옴표 없이 실제 여러 줄 원문을 넣는다.
자유 형식 질문은 `role:"user"`다. `system`은 고정 형식 경보에만 사용한다.

이미 backend에 저장한 thread를 과거 체크포인트에서 fork·rollback하면,
그래프와 업무 DB의 revision 차이로 저장이 409가 될 수 있다. 외부 DB 저장은
체크포인트와 함께 되돌아가지 않으며, 현재 초기 revision의 자동 재동기화는
구현하지 않았다. 독립적인 경보 실험은 Threads 패널 상단 **New**로 새 thread를
만들고, 일반 후속 질문은 현재 thread의 최신 상태에서 보낸다.

`langgraph dev`는 실험용이다. 대화 체크포인트는 PostgreSQL이 아니라
`agent_dev_state` 볼륨의 로컬 개발 저장소에 남는다. 업무 조사 데이터는
backend PostgreSQL에 남는다. 두 저장소는 함께 보존해야 한다.
기존 agent PostgreSQL 대화나 예전 localStorage 이력의 자동 이관은 하지 않는다.

## 이번 범위에서 제외한 것

- 동일 경보의 새 조사 중복 생성 방지
- 저장 실패 재시도·복구 정책
- 승인 취소와 재승인
- 프로덕션 Agent Server 배포

실제 실행·테스트 증거는 `docs/agent-server-validation.md`에 기록한다.
