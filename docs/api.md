# TRACE v1.0.0 HTTP API

기준: `backend/main.py`, `backend/v1_models.py`, `v1_auth.py`, `v1_commands.py`, `v1_store.py`와 [통합 계약](v1-contract.md). 공개 경로는 nginx의 `/api`다. `.env.example` 사용 시 로컬 기준 주소는 `http://localhost:18080`이다.

## 개발 신원과 접근

일반 HTTP 요청에는 `X-User-Name`, `X-User-Role`이 필수다. 이름은 `encodeURIComponent(name)`으로 URL 인코딩한다. 역할은 `worker`, `engineer`, `admin`이다. 누락·빈 이름·잘못된 역할은 401이다. 이는 목업 신원이며 실제 로그인 인증이 아니다. Keycloak 연동은 후속 범위다.

| 역할 | 목록·상세·이벤트·SSE | 재질문 답변 | 승인·수정 |
|---|---|---|---|
| worker | 본인 작업 | 본인 작업만 | 불가 |
| engineer | 전체 | 본인 작업만 | 승인 대기 작업 |
| admin | 전체 | 본인 작업만 | 불가 |

담당자 배정 기반 제한은 없다. 본인 작업 여부는 디코딩한 요청자 이름으로 비교한다. 조회·답변 범위 밖 작업은 404, 검토 역할 위반은 403, 잘못된 상태·중복 경쟁 명령은 409, 본문·커서 검증 실패는 422다. 오류는 `detail` 필드로 반환한다.

## 공개 경로

모든 `{id}`는 UUID다. JSON은 UTF-8, 시각은 ISO 8601이다.

| 메서드 | 경로 | 요청·응답 |
|---|---|---|
| POST | `/api/ai/tasks` | `{question}` -> 202 `{taskId}` |
| GET | `/api/ai/tasks` | 200 접근 가능한 작업 배열, 최신순; 미완료 포함 |
| GET | `/api/ai/tasks/{id}` | 200 작업과 메시지·이벤트·검토·승인 스냅샷 |
| POST | `/api/ai/tasks/{id}/messages` | `{text}` -> 202 `{taskId}`; 요청자, WAITING_INPUT |
| POST | `/api/ai/tasks/{id}/approval` | 검토 결정 -> 202 `{taskId}`; engineer, WAITING_APPROVAL |
| GET | `/api/ai/tasks/{id}/events?after=0` | 200 `seq > after` 이벤트 배열 |
| GET | `/api/ai/tasks/{id}/stream` | SSE; 아래 신원·커서 쿼리 사용 |
| GET | `/api/ai/investigations` | 200 저장된 승인 조사 배열(승인 최신순); worker는 본인 것만 |
| GET | `/api/ai/investigations/{id}` | 200 승인 조사 하나; 저장 전이거나 볼 수 없으면 404 |
| GET | `/api/sops` | 200 `sop-ocap/` SOP·OCAP 요약 배열(`markdown` 제외) |
| GET | `/api/sops/{id}` | 200 요약 + `markdown` 원문; 없으면 404 `{"detail":"문서를 찾을 수 없습니다."}` |

승인 이력 응답은 `id`, `user_name`, `user_role`, `question`, `status:"DONE"`, `report`, `approved_by`, `approved_role`, `event_time`, `lot_id`, `approved_at`, `created_at`, `updated_at`이며 대화·이벤트·검토 이력은 포함하지 않는다. SOP 응답 필드는 `id`, `title`, `category`(`SOP`/`OCAP`), `version`, `updatedAt`, `owner`, `description`, `tags`, `demo`이며 문서 머리 표(`| 담당 팀 | 버전 | 최근 개정 |`)에서 읽는다.

### 생성과 재질문

```json
{"question":"ETCH-07 CH-B OX-120 endpoint 지연 118초, RF reflected power 상승 29W"}
```

`question`과 답변 `text`는 공백만 아닌 1~10,000자다. 생성은 모든 지원 역할에 허용된다. `tool`, `run_id`, 분류, 담당자 필드는 받지 않는다. 이상 현상과 범위(장비·챔버·레시피 중 하나)가 부족하면 `QUESTION {text,missing}` 이벤트와 `WAITING_INPUT` 상태가 된다.

```json
{"text":"ETCH-07 CH-B에서 발생했고 레시피는 OX-120입니다"}
```

답변은 원래 요청자만 가능하며 재개 결과는 상세·이벤트·SSE로 확인한다. 세 차례 보완 후에도 부족하면 `INCOMPLETE`다.

### 검토

```json
{"action":"revise","comment":"RF 관련 근거를 다시 확인해 주세요"}
```

```json
{"action":"approve","comment":"확인 가설과 근거 검토","event_time":"2026-10-20T01:00:00Z","lot_id":"LOT-1"}
```

`action`은 `approve` 또는 `revise`, `comment`는 기본 빈 문자열이며 최대 10,000자다. `event_time`과 `lot_id`는 선택 메타데이터이며 `lot_id`는 최대 200자다. 검토자 이름은 요청 신원에서 서버가 결정한다. 본문의 `reviewer`, `by`, `category` 같은 추가 필드는 허용하지 않는다.

수정은 기존 근거·수치를 보존하고 feedback을 추가한 보고서로 다시 검토를 기다린다. 템플릿 모드에서는 수정 요청을 기록하되 임의 문장 편집을 수행했다고 주장하지 않는다. 승인은 검토 당시 보고서 스냅샷을 기록하고 agent의 DONE 콜백 뒤 승인 이력을 확정한다. 승인 대기 상태를 조건부로 확보하므로 경쟁 검토가 모두 재개되지는 않는다.

### 상세와 이력

작업 필드: `id`, `user_name`, `user_role`, `question`, `command_id`, `status`, `report`, `created_at`, `updated_at`. 상세에는 다음이 추가된다.

- `messages`: 첫 질문, 추가 답변, agent 재질문. 발화 역할·신원·시각 포함.
- `events`: `task_id`, `seq`, `event_id`, `type`, `payload`, `created_at`.
- `reviews`: action·comment·검토자 신원·검토 당시 report·선택 메타데이터·시각.
- `investigation`: 승인 스냅샷 또는 null. `review_id`, `approved_by`, `approved_role`, `approved_at`, `event_time`, `lot_id`, report 등 포함.

초안·메시지·이벤트는 승인 전에도 영속 저장된다. 현재 report와 승인 당시 스냅샷은 서로 다를 수 있다. 이력 조회는 제공하지만 승인 기록을 다음 조사의 검색 근거로 사용하는 기능은 미래 범위다. 과거 브라우저 localStorage 기록은 로컬 읽기 전용이며 이 API의 서버 이력과 다르다.

## 상태와 SSE

상태는 `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_APPROVAL`, `DONE`, `INCOMPLETE`, `FAILED`다. 답변·검토는 대기 상태를 RUNNING으로 되돌린다. 뒤의 세 상태는 종료 상태다.

`EventSource`는 사용자 정의 헤더를 설정하지 못하므로 SSE만 `user_name`, `user_role` 쿼리로 목업 신원을 받는다.

```js
const url = `/api/ai/tasks/${id}/stream?user_name=${encodeURIComponent(name)}&user_role=${role}&after=${lastSeq}`;
const source = new EventSource(url);
for (const type of ['DONE', 'INCOMPLETE', 'FAILED']) {
  source.addEventListener(type, () => source.close());
}
```

각 SSE 이벤트는 `id: <seq>`, `event: <TYPE>`, `data: <JSON>`이다. `data`에는 payload와 `at` 시각이 들어간다. 서버는 `after`와 `Last-Event-ID` 중 큰 커서보다 뒤의 이벤트만 재생한다. 커서는 음수가 아닌 정수다. 클라이언트는 작업별 `seq`로 중복 제거하고 마지막 커서를 보존한다. 새로고침은 상세 조회로 전체 이력을 복원한 뒤 이어받는다. 빈 조회 주기에는 keep-alive 주석을 보내며 종료 상태의 이벤트를 전달한 뒤 스트림을 닫는다.

| 이벤트 | payload / 의미 |
|---|---|
| QUEUED | `{by}` 생성 |
| RUNNING | 실행·답변·검토 재개 |
| MESSAGE | `{text,by}` 추가 사용자 답변 |
| QUESTION | `{text,missing}` 재질문 |
| SEARCH_STARTED | 사례 검색 시작 |
| ANALYSIS_STARTED | 통계·문서 조회 시작 |
| REPORT_STARTED | 보고서 구성 시작 |
| APPROVAL_REQUIRED | `{report}` 검토 대기 |
| REVIEWED | `{action,comment,event_time,lot_id,by,role}` 검토 접수 |
| DONE | `{report,approved,by}` 승인 후 완료 |
| INCOMPLETE | `{reason}` 정보 또는 사례 근거 부족 |
| FAILED | `{error}` 실행·전달·중단 오류 |

보고서는 `context`, `scored`, `metrics`, `causeCases`, `docIds`, `documents`, `summary`, `unknowns`, `feedback`, `demo:true`를 포함한다. `documents`는 `{id,title,text}` 배열이다. 수치 항목은 단위와 근거 사례 ID를 보존한다. 현재 RAG는 샘플 문서 ID 조회이며 실제 원인을 확정하지 않는다.

## 내부 HTTP 경계

공개 브라우저에서 호출하지 않는다. backend 내부 API와 agent 실행에는 `X-Internal-Key`가 필수다.

| 호출 | 경로 | 본문·용도 |
|---|---|---|
| backend -> agent | POST `/internal/tasks/{id}/run` | `{question}` 또는 `{resume:{text}}`, `{resume:{action,comment,by}}` |
| agent -> backend | POST `/internal/tasks/{id}/events` | `{event_id,type,payload}` |
| business MCP -> backend | GET `/internal/cases` | 샘플 사례 배열 |

agent 실행에는 `X-Command-ID`가 필수이며 agent는 현재 명령 ID를 실행 config에 넣어 이벤트 콜백으로 전달한다. backend는 동일 command ID 헤더를 요구한다. 명령별 event ID 중복은 재반영하지 않고, 이전 명령의 지연 콜백은 409로 거절한다. 이 문서 정리에서는 서비스 코드를 수정하거나 테스트 통과를 확인하지 않았다.

## curl

```bash
curl -sS http://localhost:18080/api/ai/tasks \
  -H 'Content-Type: application/json' \
  -H 'X-User-Name: worker-demo' -H 'X-User-Role: worker' \
  -d '{"question":"endpoint 지연 118초"}'
# 반환된 UUID를 사용한다.
curl -sS http://localhost:18080/api/ai/tasks/<taskId> \
  -H 'X-User-Name: worker-demo' -H 'X-User-Role: worker'
curl -N 'http://localhost:18080/api/ai/tasks/<taskId>/stream?user_name=worker-demo&user_role=worker&after=0'
```
