# SOP retrieval experiment

`sop/`의 SOP/WI/SPEC 7개를 조항별로 검색하는 독립 실험이다.
이 문서의 적재·검색·평가 CLI는 독립 실행이다. 기존 RAG MCP의 `search_sop`도 같은 청킹·벡터·재순위화 모듈을 사용하되, 별도 `sop-postgres` 저장소를 운용한다.
답변 생성이나 장비 조치는 수행하지 않는다.

현재 기본 방법은 **small 임베딩 후보 20개 → LLM 재순위화 → 조항 3개 반환**이다.
원래 세트 13/13, 추가 고정 세트 8/8을 확인했다.
문제 정의·대안 비교·실패한 모델 교체 실험·비용·한계는
[검색 개선 의사결정 기록](../docs/development/sop-rag-retrieval-decision.md)에 있다.

## 실행

저장소 루트에서:

```sh
uv sync --project mcp --group rag-experiment
docker compose -p trace-sop-rag -f mcp/sop.compose.yaml up -d --wait

uv run --project mcp --group rag-experiment python mcp/sop_experiment.py ingest
uv run --project mcp --group rag-experiment python mcp/sop_experiment.py search \
  '압력이 불안정하고 식각 속도가 떨어졌어'
uv run --project mcp --group rag-experiment python mcp/sop_experiment.py evaluate \
  --output outputs/sop-evaluation-current.json
```

- 기본 DB: `postgresql://trace:trace@localhost:55432/trace_sop`.
  서비스 DB와 다른 컨테이너·볼륨이다. 현재 실험 테이블은 `sop_rag_model_chunks`다.
  초기 `sop_rag_chunks`는 삭제하지 않고 스냅샷으로 남겨 두었다.
- DB 변경: `SOP_DATABASE_URL` 또는 각 명령의 `--database-url`.
  `SOP_DB_PORT`로 포트를 변경하면 DB URL도 맞춘다.
- 기본 키 파일: 저장소 옆 `../etch_trace_poc/.env`.
  각 명령의 `--env-file /absolute/path/.env`로 변경한다.
  `OPENAI_API_KEY`만 읽으며 다른 프로젝트의 DB·모델 설정은 가져오지 않는다.
- 기본 검색은 조항 3개를 반환한다. 출력은 원문·출처·개정·시연 표시·원래 코사인 거리의 JSON이다.
  재순위화 후 거리는 오름차순이 아닐 수 있다.
- 임베딩 검색만 비교: `search --method dense --top-k 5`.
  기본 `rerank` 방법에서 `--top-k`는 3만 허용한다.
- 모델 비교: `--model text-embedding-3-small` 또는 `--model text-embedding-3-large`.
  해당 모델로 `ingest`한 뒤 검색한다. 모델별 벡터와 캐시를 분리한다.
- 실험 DB 종료: `docker compose -p trace-sop-rag -f mcp/sop.compose.yaml stop`.
  볼륨은 유지되므로 재시작하면 적재한 문서를 계속 사용할 수 있다.

## 적재 방식

`README.md`와 `00_식각공정_조사.md`는 제외한다.
`##`와 `###`의 번호 있는 절을 분리하고, 내용이 없는 상위 절과 개정 이력은 제외한다.
상위 절에 소개 문장이 있으면 별도 조항으로 보존한다. 표·목록은 분리하지 않는다.

기존 `SOP-ETCH-12#4.2` 등의 ID를 유지한다.
임베딩 입력은 문서 제목·상위 절 제목·조항 제목·원문이다.
공통 주의문은 검색 입력에서 제외하되 결과 메타데이터에는 보존한다.
`[예시]` 표시는 삭제하지 않고, 모든 결과에 `is_demo: true`를 보존한다.
이는 실제 장비 판정 기준이 아니라 시연용 문서 검색이다.

기본 임베딩은 OpenAI `text-embedding-3-small`, 1536차원이다.
정확 코사인 검색 후보 20개를 `gpt-4.1-mini`가 읽고 조항 ID 3개를 선택한다.
후보 밖 ID와 중복 ID는 거절하며 원문 근거를 생성하지 않는다.
인덱스·키워드 결합·교차 참조 확장은 아직 적용하지 않는다.
내용·메타데이터 해시가 같은 조항은 임베딩을 재사용한다.
재적재하면 수정된 조항을 갱신하고 원문에서 삭제된 조항을 해당 모델에서만 제거한다.
이 테이블은 지정한 SOP 폴더 전체의 현재 스냅샷이므로 다른 문서 저장 용도로 공유하지 않는다.
적재 도중 실패하면 DB 변경을 롤백한다.

## 평가

`sop_questions.json`을 검색 실행 전에 고정한다.

- 직접 질문 5개, 바꿔 말한 질문 5개, 복수 조항 질문 3개
- 문서 밖 질문 2개는 결과와 거리만 기록하고 성공률에서 제외
- 질문별 필요한 조항이 **모두 top-3에 포함**되어야 성공
- 목표: 답이 있는 질문 **11/13 이상**. 미달이면 `evaluate` 종료 코드 1
- 문서 밖 질문도 가까운 문서를 반환할 수 있다. 거리 임계값으로 답 없음 판정을 하지 않는다.
- 현재 15문항은 초기 실험용이며 일반적인 검색 품질을 보장하는 별도 평가 세트는 아니다.

평가 JSON은 모델·검색 방법·질문 파일 SHA-256·원래 정답 순위·토큰·시간을 기록한다.
`tokens`는 질문 임베딩 사용량이고, 재순위화 사용량은 `rerank_input_tokens`와
`rerank_output_tokens`다. 문서 밖 질문을 판정하는 기능은 아직 없다.

### 최초 실행 결과 (2026-10-20)

7개 문서에서 64개 조항을 적재했다. 현재 임베딩 입력은 10,807토큰,
15개 평가 질문은 577토큰이다. 재적재 시 변경이 없으면 임베딩 0건·0토큰이다.

| 구분 | 성공 |
|---|---|
| 직접 질문 | 5/5 |
| 바꿔 말한 질문 | 1/5 |
| 복수 조항 질문 | 2/3 |
| 합계 | **8/13 (목표 11/13 미달)** |

실패 질문은 P1·P3·P4·P5·M1이다.
공통 주의문을 임베딩에 포함한 최초 버전도 8/13이었으며,
반복 주의문을 제외해도 성공 문항은 늘지 않았다. 질문과 정답 ID는 바꾸지 않았다.
두 결과는 각각 `outputs/sop-evaluation.json`, `outputs/sop-evaluation-context.json`에 있다.
이 파일은 로컬 실행 산출물이며 Git에 포함하지 않는다.

한국어로 바꿔 쓴 계통 용어와 복수 주제 질문의 근거 누락이 확인됐다.
예를 들어 P1은 RF 점검 순서 대신 안전·에너지 차단 절차를,
M1은 RF 조항만 반환하고 endpoint 동시 비교 조항을 놓쳤다.
문서 밖 질문도 결과가 반환되므로 이 상태를 답변 가능한 검색으로 간주하지 않는다.
후속 실험은 동일 질문을 유지한 모델 비교나 용어 정규화부터 제안한다.
이 결과는 현재 방법 적용 전의 기준선이다. 현재 결과와 선택 과정은 위 의사결정 기록을 따른다.

## 테스트

```sh
SOP_TEST_DATABASE_URL=postgresql://trace:trace@localhost:55432/trace_sop \
  uv run --project mcp --group rag-experiment python -m unittest discover \
  -s tests -p 'test_sop*.py' -v
```

파서·메타데이터·평가 집계를 검사한다. DB 테스트는 트랜잭션마다 고유 스키마를
사용하고 롤백하며, OpenAI 임베딩 응답만 대체하고 실제 pgvector 적재·검색을 실행한다.
DB 환경변수를 생략하면 DB 테스트는 건너뛴다.
