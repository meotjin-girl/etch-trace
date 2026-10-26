# Agent 개발과 LangSmith 실험 가이드

## 1. 개념과 적용 범위

**Trace는 한 번의 실행을 들여다보는 기록이고, Experiment는 같은 문제집으로 변경 전후를 비교하는 평가다.**

- Trace: 어느 노드를 지났는지, 어떤 근거를 가져왔는지, 어디서 실패했는지 확인한다.
- Dataset: 고정 질문과 기대 결과를 저장한 문제집이다.
- Evaluator: 결과가 기준을 지켰는지 점수를 매기는 함수다.
- Experiment: 특정 코드·프롬프트·모델을 데이터셋에 실행한 결과 묶음이다.

처음에는 trace부터 연결한다. 다음으로 작은 데이터셋을 만들어 기준선을 남긴다.
그 뒤 한 번에 한 요소만 바꾸고 같은 데이터셋으로 비교한다.
그래프나 프롬프트를 바꾸지 않은 채 모델만 바꿨다면 그 사실도 기록한다.

## 2. 키 설정과 첫 추적

저장소 루트 `.env`를 편집한다. 이미 파일이 있다면 덮어쓰지 않는다.
없을 때만 `.env.example`을 복사한다. 실제 키는 `.env.example`에 넣거나 커밋하지 않는다.

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<발급받은 LangSmith 키>
LANGSMITH_PROJECT=etch-trace-developer-dev
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
```

- 팀원별 개발 프로젝트 이름을 구분한다: `etch-trace-<개발자 식별자>-dev`.
- 공통 비교 실험은 같은 데이터셋을 사용한다. 프로젝트 분리는 데이터셋 분리와 다르다.
- EU 워크스페이스라면 endpoint를 `https://eu.api.smith.langchain.com`으로 바꾼다.
- 키가 특정 workspace 지정을 요구하면 해당 `LANGSMITH_WORKSPACE_ID`를 입력한다.
- 추적을 켜면 경보·질문·근거·후보 같은 실행 데이터가 LangSmith로 전송된다. 처음에는 합성 경보로 확인한다.

이하 명령은 저장소 루트에서 기본 Compose 프로젝트로 실행하는 경우를 기준으로 한다.
이미 `-p <프로젝트명>`으로 스택을 실행했다면 모든 명령에 같은 `-p` 값을 사용한다.
예를 들어 별도 검증 스택의 이름은 `etchtrace-v1`이었다.

실행 중인 스택에 환경변수를 반영하려면:

```sh
docker compose -f compose.yaml up -d --no-deps --wait agent
```

이 명령은 변경된 Agent 환경변수를 반영한다. 새 체크아웃에서는 먼저 전체 스택을 실행한다.

```sh
docker compose -f compose.yaml up -d --build --wait
```

경보 run이 하나 생기거나(모의 장비 경보, 또는 Studio에서 경보 입력) `.env`의 `WEB_PORT`
화면(예제 설정은 `http://localhost:18080`)의 조사에서 질문을 한 번 보낸 뒤 LangSmith의 위
프로젝트에서 `prepare → agent ↔ tools → reason → publish` 노드 실행이 나타나는지 확인한다.
후속 질문은 같은 thread의 별도 run이다. 조사 ID와 `thread_id`가 같으므로 이 값으로 관련
실행을 찾는다. Studio 연결은 [agent-server.md](agent-server.md#studio와-저장소)를 따른다.

키를 출력하지 않고 컨테이너 설정 여부만 확인하려면:

```sh
docker compose -f compose.yaml exec -T agent uv run --no-sync python -c \
  "import os; print('tracing:', os.getenv('LANGSMITH_TRACING')); print('key configured:', bool(os.getenv('LANGSMITH_API_KEY'))); print('project:', os.getenv('LANGSMITH_PROJECT'))"
```

LangSmith 키는 OpenAI 키가 아니다. LLM 없이도 그래프 실행 추적은 가능하다.
`LANGSMITH_TRACING=false`는 일반 실행의 자동 추적을 끄는 설정이다.
뒤의 `Client.evaluate(...)`를 명시적으로 실행하면 실험 결과 업로드는 별도로 수행된다.
현재 Agent는 `OPENAI_MODEL`(기본 `gpt-4.1-mini`)로 도구 선택·후보 구성·질의응답을 한다.
OpenAI 변수를 설정한다고 자유로운 조사·보고서 작성 Agent로 바뀌지는 않는다.
직접 HTTP로 호출하는 모델의 토큰·비용 세부 추적, 별도 MCP 서버 내부의 분산 추적은
아직 구현하지 않았다. 우선 Agent 노드와 MCP 반환 결과를 추적한다.

## 3. 보통의 개발·실험 순서

1. **목표를 하나 정한다.** 예: “압력 경보에서 OCAP-ETCH-PRS 근거가 앞 3개 후보에 들어가게 한다.”
2. **10~20개의 고정 입력을 만든다.** 정상 경보만 넣지 말고 맞는 조항이 없는 경보·복합 경보·후속 질문을 넣는다.
3. **현재 코드로 baseline을 실행한다.** 결과를 남기지 않고 코드를 먼저 바꾸지 않는다.
4. **한 요소를 바꾼다.** 프롬프트, 모델, 도구 설명, 검색 방식 중 하나를 먼저 바꾼다.
5. **같은 문제집으로 candidate를 실행한다.**
6. **실패한 입력의 trace를 본다.** 점수만 보지 말고 어느 노드·도구 결과에서 차이가 났는지 확인한다.
7. **회귀 테스트를 통과시키고 PR에 비교 결과를 적는다.**

팀원이 작업할 경계(`agent/src/trace_agent/`):

| 개선 대상 | 파일 |
|---|---|
| 경보 텍스트 파싱 | `alert_text.py` |
| 그래프 구성 | `graph.py` |
| 노드(준비·ReAct·후보·저장) | `nodes.py` |
| 시스템 지시문 | `prompts.py` |
| 모델 호출·구조화 출력 | `model.py` |
| 도구 선언 | `tools.py` |
| MCP 전송 | `evidence.py` |
| 후보·입력 계약 | `models.py`, `state.py` |
| 사례 유사도·수치 계산 | `mcp/evidence.py`, `mcp/physics_models.py` |

후보 필드와 저장 계약을 유지하면 보통 프론트·백엔드를 바꿀 필요가 없다.
모델이 수치를 다시 계산하게 만들지 않는다. 단위·값·사례·문서 ID는 결정론적 도구 결과를 유지한다.

## 4. 첫 Dataset과 평가 기준

LangSmith에서 `etch-trace-agent-v1` 데이터셋을 만들고 다음 예시부터 추가한다.
inputs는 graph 입력 봉투 그대로이고, reference outputs는 기대 문서 ID다.

| inputs | reference outputs |
|---|---|
| `{"request":{"role":"system","content":"[경보] ETCH-02 / CH-A / Lot DEMO-LOT / Wafer W01 / RCP-OX-ETCH-EDU-01\n- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W (한계 37 W) (OCAP-ETCH-RF)"}}` | `{"expected_doc":"OCAP-ETCH-RF"}` |

경보 텍스트 문법은 [agent-request.md](agent-request.md)를 따른다. 압력·가스·온도 경보, 맞는 조항이 없는 경보를 추가한다.
후속 질문은 같은 thread가 필요하므로 단일 경보 평가와 분리한 시나리오 데이터셋으로 만든다.

처음부터 LLM judge 하나로 모든 결과를 평가하지 않는다.

| 기준 | 추천 검사 |
|---|---|
| 경보 조사가 후보를 만들었는가 | 후보 수 ≥ 1 |
| 기대 OCAP 문서가 앞 3개 후보에 있는가 | `doc_ids` 접두사 비교(hit@3) |
| 존재하는 사례·문서만 인용했는가 | ID 집합 검사 |
| 통계·물리 수치가 정확한가 | 도구의 단위 테스트 |
| 승인 전에 조치를 기록하지 않는가 | backend API 통합 테스트 |
| 후보 설명이 이해하기 쉬운가 | 사람의 rubric 평가, 이후 보조 LLM judge |

“정확한 원인을 맞췄는가”를 기본 정답으로 잡지 않는다.
현재 데이터는 합성 경보와 문서에 기반한 확인 가설이지 현장 원인 확정 자료가 아니다.

## 5. Docker 안에서 업무 저장 없이 비교하기

다음 예시는 실제 MCP 조회 도구와 모델을 사용하지만, `upsert_live_investigation`만
가로채 backend에 조사를 만들지 않는다. 체크포인터 없이 실행하므로 Agent Server의 thread도
남지 않는다. 각 예시는 새 thread ID로 실행한다. 모델 호출 비용이 발생한다.

먼저 위 데이터셋과 키를 준비한 뒤 저장소 루트에서 실행한다.
이 코드는 실험 실행 예시이며 별도 운영 evaluator 서비스가 설치된 것은 아니다.

```sh
docker compose -f compose.yaml exec -T agent uv run --no-sync python - <<'PY'
import asyncio
from uuid import uuid4
from langsmith import Client
from trace_agent.config import Settings
from trace_agent.evidence import MCPEvidence
from trace_agent.graph import build_graph

class DryRun:
    """Real MCP reads; the business write returns the receipt without saving."""
    def __init__(self):
        self.real = MCPEvidence(Settings())
    async def call(self, service, name, arguments):
        if name == "upsert_live_investigation":
            tid = arguments["thread_id"]
            return {"id": tid, "thread_id": tid,
                    "revision": arguments["payload"]["base_revision"] + 1}
        return await self.real.call(service, name, arguments)

graph = build_graph(DryRun())

def target(inputs):
    result = asyncio.run(graph.ainvoke(
        {"request": inputs["request"]},
        config={"configurable": {"thread_id": str(uuid4())}},
    ))
    return {"candidates": [c.model_dump(mode="json") for c in result.get("candidates", [])]}

def hit_at_3(outputs, reference_outputs):
    docs = [d for c in outputs["candidates"][:3] for d in c["doc_ids"]]
    return {"key": "hit_at_3",
            "score": int(any(d.startswith(reference_outputs["expected_doc"]) for d in docs))}

results = Client().evaluate(
    target,
    data="etch-trace-agent-v1",
    evaluators=[hit_at_3],
    experiment_prefix="baseline",
    metadata={"change": "current ReAct agent"},
    max_concurrency=1,
)
results.wait()
PY
```

변경 후에는 `experiment_prefix="candidate-prompt-v2"`처럼 이름을 바꾼다.
`metadata`에 변경 내용·Git commit·모델명·데이터 버전을 남긴다.
미커밋 변경을 비교했다면 그 차분도 PR에 제시한다.
모델 출력에 변동이 있다면 `num_repetitions`로 같은 입력의 반복 평가도 검토한다.

LangSmith UI에서는 다음 순서로 비교한다.

1. **Datasets & Experiments**에서 사용한 데이터셋을 연다.
2. baseline 실험을 연다. 입력·기대 출력·실제 출력과 `hit_at_3` 점수를 확인한다.
3. **Compare**에서 candidate 실험을 추가한다.
4. **Comparing 2 Experiments** 화면에서 같은 입력의 두 출력과 점수를 나란히 확인한다.
5. 실패한 행의 실행 상세나 **View tracing**으로 노드별 원인을 조사한다.

기본 Compose는 MCP 포트를 공개하지 않으므로 처음에는 컨테이너 안에서 실험하는 편이 간단하다.
브라우저와 Studio는 전체 사용자 흐름 확인, 데이터셋 실험은 Agent 변경 비교에 사용한다.

## 6. 팀원에게 요청할 PR 항목

- 무엇을 개선했고 어떤 계약을 유지했는가
- 데이터셋 이름·버전, baseline/candidate의 Experiment 이름 또는 링크
- 자동 평가 점수 변화와 사람이 확인한 실패 예시
- 모델을 사용했다면 모델명·설정·호출 횟수
- `cd agent && uv run pytest -q` 결과
- 조사·대화 계약을 바꿨다면 `tests/check_agent_server.mjs` 확인 결과

## 7. 검증 기록과 한계 (이전 그래프 기준)

아래는 제거된 이전 다단계 그래프와 `stage_match` 평가로 확인한 기록이다. 현재 ReAct Agent의 5장 예시는 아직 같은 방식으로 기록하지 않았다.

2026-10-20, 분리된 Docker 테스트 스택과 실제 LangSmith 워크스페이스에서 확인했다.
실제 키는 Git에 포함하거나 로그로 출력하지 않았다.

| 검사 | 관찰 결과 |
|---|---|
| Compose 설정 | LangSmith 5개·OpenAI 2개 설정이 Agent에만 전달됨 |
| 브라우저 질문 제출 | 샘플 질문이 검토 대기까지 진행하고 LangGraph 루트 실행이 저장됨 |
| 평가 코드 | 본문의 target·evaluator를 실제 MCP 서비스와 실행함 |
| 샘플 평가 데이터셋 | `etch-trace-agent-smoke-v1`, 정상 질문·장비 정보 누락 질문 2개 |
| 첫 실험 | `smoke-baseline-d88fe32d`, 2/2 완료, `stage_match` 평균 1.00 |
| 반복 실험 | `smoke-replay-2187366b`, 2/2 완료, `stage_match` 평균 1.00 |
| Aside 비교 화면 | Compare로 두 실험을 추가하고 예시별 출력·점수를 확인함 |
| Aside 실행 상세 | 같은 예시의 A/B 결과를 열고 Traces에서 중첩 실행을 확인함 |
| Agent 회귀 | 실제 PostgreSQL 재시작 검사를 포함해 25개 통과 |

위 두 실험은 같은 코드의 반복 실행이다. 성능 개선이나 모델 우열의 증거가 아니라
**추적·평가·비교 경로가 동작한다는 연동 검사**다. 모델 호출은 발생하지 않았으며,
정답 근거·수치 보존·보고서 품질 같은 평가는 별도로 추가해야 한다.
실험 target은 승인 전 interrupt에서 멈추며 업무 task API에 이력을 저장하지 않는다.
브라우저에서 제출한 연결 확인용 조사 한 건만 일반 업무 테스트 이력에 남는다.

`upload_results=False`는 업무 DB 저장 여부를 제어하는 옵션이 아니다.
SDK 평가 중 중첩 추적까지 완전히 차단하려면 별도 추적 비활성화 처리가 필요하다.
완전 오프라인 검사에는 우선 Agent의 단위 테스트를 사용한다.
검증용 실행에서는 셸 환경변수로 추적을 일시 활성화했다.
일반 실행은 루트 `.env` 설정으로 복원하며, 지속 추적은 해당 파일에서 명시적으로 활성화한다.

## 공식 자료

- https://docs.langchain.com/langsmith/trace-with-langgraph
- https://docs.langchain.com/langsmith/evaluation-quickstart
- https://docs.langchain.com/langsmith/evaluate-llm-application
