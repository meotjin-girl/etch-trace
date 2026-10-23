# backend → agent 조사 요청 형식

backend가 agent에 조사를 요청하는 경로는 두 개다. 요청 본문 형식은 하나로 고정하고, `role`로 출처를 구분한다.

```http
POST {AGENT_URL}/internal/tasks/{task_id}/run
X-Internal-Key, X-Command-ID, X-Requester-Name, X-Requester-Role   (기존과 동일)

{"role": "system" | "user", "content": "<문자열>"}
```

| role | 언제 | content |
|---|---|---|
| `user` | 사용자가 화면에서 질문 입력 (`POST /api/ai/tasks {question}`) | 사용자가 쓴 문장 그대로 |
| `system` | Prometheus 경보 firing (모의 장비 알람 + FDC 규칙) | 아래 **고정 형식 텍스트** |

- `content`는 두 경우 모두 문자열이다. 줄바꿈은 `\n`이다.
- 이 `role`은 **backend→agent 요청 봉투**의 필드다. agent 내부에서 LLM을 부를 때 쓰는 messages의 `system`/`user`(`agent/agents/common.py::_ask_model`)와는 다른 층위다.
- 재개 요청 `{"resume": {...}}`(재질문 답변, 검토 결과)는 바뀌지 않는다.
- 시스템 요청 작업의 요청자는 `FAB-ALERT`(role `user`, user_id 없음)다.
  - 이 값은 `X-Requester-Name`/`X-Requester-Role` 헤더로 전달된다.
  - 작업 목록에서 시스템이 만든 작업을 구분하는 기준이 된다.
- 엔지니어 승인 흐름(`APPROVAL_REQUIRED` → `/approval`)은 두 경로가 같다.

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

## 묶음·마감·중복 규칙 (backend `v1_alerts.py`)

1. backend가 `PROMETHEUS_URL`의 `/api/v1/alerts`를 5초마다 폴링해 `firing` 경보만 읽는다. `PROMETHEUS_URL`이 비어 있으면 이 경로는 꺼진다.
2. 경보의 `activeAt` 시각에 `etch_run_info{tool,chamber}`를 조회해 Lot을 정한다.
3. 경보를 (장비, 챔버, Lot) key로 묶는다. key 형식은 `ETCH-02/CH-A/SIMLOT-…`다.
4. 다음 중 먼저 오는 시점에 묶음을 닫는다:
   - 그 챔버의 현재 Lot이 바뀜 (run 종료)
   - 첫 경보를 본 뒤 90초가 지남
5. 닫을 때 run 구간(`activeAt − etch_sample_offset_seconds` ~ 마감 시각, 최대 125초)의 센서 12종을 `query_range`(5초)로 조회하고 정상 통계와 함께 텍스트로 만든다.
6. `v1_alert_tasks`(key가 PRIMARY KEY)와 작업을 한 트랜잭션에 만든다. 이미 있는 key의 경보는 무시한다.
   - backend가 재시작해도 같은 Lot으로 작업이 두 번 생기지 않는다.
   - 묶음을 닫은 뒤 같은 Lot에서 뜬 경보는 새 작업을 만들지 않는다.
7. 작업 `question`에는 사람이 읽는 요약을 넣는다(예: `ETCH-02/CH-A SIMLOT-… 경보 3건: FDC_WATCH, RF_REFLECT_HIGH`). 첫 메시지에는 agent에 보낸 content 원문을 넣는다.
   - 묶음 원자료(JSON)는 `v1_alert_tasks.bundle`에 근거로 보존한다.

Prometheus는 backend 컨테이너에서 `http://host.docker.internal:9090`(로컬 `backend/prometheus/compose.yaml`)로 접근한다.

## agent 담당자 할 일 (backend는 이미 이 형식으로 보냄)

현재 agent `InitialRequest`는 `{question}`만 받는다(`extra="forbid"`). 그래서 새 본문은 **422로 거절되고 작업은 FAILED**가 된다. 질문 경로도 마찬가지다. 이 backend 변경은 아래 agent 변경과 함께 머지해야 한다.

1. `InitialRequest`를 `{role: Literal["system","user"], content: str}`로 바꾼다.
2. `role == "user"`: 기존 경로(`parse_question(content)` → 필요하면 재질문)를 그대로 쓴다.
3. `role == "system"`: 위 문법대로 줄 단위로 파싱한다.
   - 헤더 → `Context(equipment, chamber, recipe)`, 경보 rule·ocap → `symptom`
   - 장비 알람 줄의 `sensor=값` → `metrics`
   - 센서 줄 → `AgentState.sensor_data`
   - 재질문하지 않는다. content 원문을 LLM user 메시지에 그대로 넣어도 된다.
4. 데모 사례(`db/cases.json`, ETCH-07/09)는 모의 장비와 맞지 않는다. 그래서 system 요청에서는 사례가 0건이어도 INCOMPLETE로 끝내지 않는다.
5. SOP 검색 query에 경보의 `ocap` ID를 포함한다.
