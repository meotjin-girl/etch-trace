# Agent 조사 요청 형식

Agent Server 그래프 `trace`의 입력은 요청 봉투 하나로 고정하고, `role`로 출처를 구분한다.

```json
{"request": {"role": "system" | "user", "content": "<문자열>"}}
```

| role | 언제 | 누가 보내나 | content |
|---|---|---|---|
| `system` | Prometheus 경보 firing (모의 장비 알람 + FDC 규칙) | backend `agent_server_alerts.py`, 내부 키 | 아래 **고정 형식 텍스트** |
| `user` | 엔지니어가 조사 화면에서 질문 | 브라우저 `/agent/threads/{id}/runs/stream`, Keycloak Bearer | 사용자가 쓴 문장 그대로 |

- `content`는 두 경우 모두 문자열이다. 줄바꿈은 `\n`이다.
- 이 `role`은 **요청 봉투**의 필드다. Agent는 이를 보고 system 경보를 구조화할지, user 대화 발화로 다룰지 결정한다. LLM 내부 system prompt와는 다른 층위이며, 경보는 사람 메시지로 대화에 추가된다.
- 한 thread의 경보(system)는 한 번만 받는다. 두 번째 system 봉투는 거절된다.

backend는 경보 묶음마다 다음 두 요청을 내부 키(`X-Internal-Key`)로 보낸다. 실행 계약 전체는 [agent-server.md](agent-server.md)에 있다.

```http
POST {AGENT_SERVER_URL}/threads                → {"thread_id": "<UUID>"}
POST {AGENT_SERVER_URL}/threads/{thread_id}/runs
{"assistant_id": "trace", "input": {"request": {"role": "system", "content": "..."}}, "multitask_strategy": "reject"}
```

## role=system content 문법

```text
[경보] ETCH-02 / CH-A / Lot SIMLOT-20261022-2A151416 / Wafer SIMLOT-20261022-2A151416-W01 / RCP-OX-ETCH-EDU-01
- 15:15:11 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)
- 15:15:31 FDC FDC_WATCH source_rf_pv_w z=-3.4 (OCAP-ETCH-RF)
- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W (한계 37 W) (OCAP-ETCH-RF)
[센서] 2026-10-22 15:14:16~15:16:16 KST, 5초 간격
- bias_rf_pv_w (W, 정상 120.134±1.448): 119.8 121.2 … 120.4
- source_rf_reflected_w (W, 정상 5.364±0.590): 5.2 6.8 5.2 … 44.1
```

| 줄 | 형식 |
|---|---|
| 헤더 (첫 줄, 1개) | `[경보] {tool} / {chamber} / Lot {lot_id} / Wafer {wafer_id} / {recipe_id}` |
| 경보 줄 (1개 이상, 시각순) | `- {HH:MM:SS} {FDC\|장비} {rule} {값 표현} ({ocap})` |
| 센서 헤더 (1개) | `[센서] {YYYY-MM-DD} {HH:MM:SS}~{HH:MM:SS} KST, 5초 간격` |
| 센서 줄 (센서명 알파벳순) | `- {sensor} ({unit}, 정상 {mean}±{sd}): {값 공백 구분}` |

- 시각은 모두 KST다.
  - 경보 시각은 Prometheus `activeAt`이다. 조건이 처음 참이 된 시각이라 pending 시작에 해당한다.
- 센서 값은 센서 헤더 구간을 5초 간격으로 나열한 순서다. 그 시각에 값이 없으면 `-`다.
- `ocap`은 `sop-ocap/` 문서 ID다(`OCAP-ETCH-*` 또는 `SOP-ETCH-12`). SOP 검색과 근거 연결에 그대로 쓴다.
- 경보 줄의 값 표현:

| rule | 출처 | 값 표현 | 의미 |
|---|---|---|---|
| FDC_WATCH | FDC | `{sensor} z={값}` | 정상 평균 대비 z-score |
| PRESSURE_TREND | FDC | `{sensor} 예측={값} mTorr` | 60초 뒤 예측 압력 |
| PRESSURE_OSC | FDC | `{sensor} σ40s={값}` | 40초 표준편차 |
| SENSOR_STALE | FDC | `{sensor} 변화={값}` | 20초 동안 값 변화 횟수(0) |
| MULTIVARIATE_FDC | FDC | `- 계통={값}` | 동시에 이탈한 계통 수 |
| 장비 알람 (PRESSURE_HIGH 등 10종) | 장비 | `{sensor}={값} {unit} (한계 {limit} {unit})` | 알람 시각의 센서값과 장비 한계 |

## 묶음·마감·중복 규칙 (backend `v1_alerts.py`, `agent_server_alerts.py`)

1. backend가 `PROMETHEUS_URL`의 `/api/v1/alerts`를 5초마다 폴링해 `firing` 경보만 읽는다. `PROMETHEUS_URL`이 비어 있으면 이 경로는 꺼진다.
2. 경보의 `activeAt` 시각에 `etch_run_info{tool,chamber}`를 조회해 Lot을 정한다.
3. 경보를 (장비, 챔버, Lot) key로 묶는다. key 형식은 `ETCH-02/CH-A/SIMLOT-…`다.
4. 다음 중 먼저 오는 시점에 묶음을 닫는다:
   - 그 챔버의 현재 Lot이 바뀜 (run 종료)
   - 첫 경보를 본 뒤 90초가 지남
5. 닫을 때 run 구간(`activeAt − etch_sample_offset_seconds` ~ 마감 시각, 최대 125초)의 센서 12종을 `query_range`(5초)로 조회하고 정상 통계와 함께 텍스트로 만든다.
6. 닫은 묶음마다 Agent Server에 thread와 run을 하나씩 만든다. 레거시 작업(`v1_tasks`)은 만들지 않는다.
   - 닫은 key는 backend 프로세스 메모리에만 기억한다. 같은 프로세스에서는 같은 Lot으로 조사가 두 번 생기지 않지만, backend가 재시작되면 다시 생길 수 있다.
   - 전달 실패는 로그만 남기고 재시도하지 않는다.
7. 조사 행은 Agent의 첫 후보 저장 때 backend에 생긴다. thread ID가 곧 조사 ID다.

Prometheus는 루트 `compose.yaml`의 `prometheus` 서비스이며 backend는 내부 이름 `http://prometheus:9090`으로 접근한다(CD 배포 서버·로컬 동일). 여러 환경이 동시에 켜져 있으면 같은 경보로 환경마다 조사가 1건씩 생긴다.

`AGENT_SERVER_URL`이 비어 있으면 backend는 레거시 경로(`v1_alert_tasks` 중복 방지 + `/internal/tasks/{id}/run`)를 쓰지만, 이전 task 실행 agent는 제거되었으므로 현재 Compose에서는 쓰지 않는다.

## Agent 요청 처리

Agent는 `request` 봉투를 `prepare` 노드에서 한 번 소비한다. `role=system` 경보는 결정론적 파서(`agent/src/trace_agent/alert_text.py`)가 헤더와 센서·알람 줄을 구조화하고 원문과 함께 대화에 추가한다. `role=user`와 후속 발화는 자연어 그대로 같은 thread에 추가된다. 표준 `{"messages":[…]}` 입력도 받는다.

Business·RAG·Physics·Sensor MCP 호출은 LLM이 현재 질문과 대화 맥락에 따라 `agent/src/trace_agent/tools.py`의 도구에서 고른다. 최종 응답은 대화 메시지와 구조화 후보이며, 후보가 바뀌면 `publish` 노드가 같은 조사에 저장한다. 경보 조사는 후보 없이 끝날 수 없다.

Agent 코드에서 자연어 질문·승인 의도 분류를 정규식으로 하지 않는다. 고정된 경보 텍스트 포맷만 결정론적 파서로 구조화하며, 도구 선택과 사용자 의도는 LLM이 대화 이력에 따라 판단한다. Physics MCP는 결정론적 식각 관계 계산에만 사용하며, 온도·압력의 원인을 시뮬레이션했다고 간주하지 않는다.
