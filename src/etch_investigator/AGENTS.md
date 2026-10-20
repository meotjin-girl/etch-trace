# CLI PROTOTYPE KNOWLEDGE BASE

## OVERVIEW

JSON 사례 기반의 별도 LangGraph CLI 패키지다. 점수 8: 높은 코드 비율, `__init__.py` 모듈 경계, 다수의 심볼과 함수; 서버와 구분되는 도메인이다.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 사용자 CLI와 `Command(resume=...)` | `cli.py` | 질문 또는 요청 JSON으로 시작 |
| 대화형 답변·기록 제안 | `chat_graph.py` | `build_chat_graph()` |
| 배치 조사·승인 그래프 | `graph.py` | `build_graph()` |
| 입력 모델·그래프 상태 | `models.py` | Pydantic 및 `AgentState` |
| 질문 추출·추가 질문 | `query.py` | 한/영 혼합 정규식 |
| 유사 사례 조회 | `repository.py`, `data/*.json` | 파일 기반, DB 사용 안 함 |
| 수치 판정·보고서 출력 | `analytics.py`, `answer.py`, `report.py` | 사례 ID와 근거 연결 |
| 계약 테스트 | `../../tests/test_workflow.py` | 두 그래프와 CLI 출력 |

## CONVENTIONS

- `__init__.py`는 `build_graph`, `build_chat_graph`만 공개한다. `cli.py`는 요청 JSON이 있으면 배치 그래프, 없으면 대화 그래프를 선택한다.
- 각 그래프는 `InMemorySaver`를 기본 체크포인터로 사용하며, 같은 `thread_id`에서 `interrupt()`를 재개한다.
- `InvestigationRepository`의 JSON 사례 점수와 `analytics.py`의 계측값 계산은 서버의 SQL 기반 도구와 별개다.
- 대화 그래프는 답변 뒤 기록 작성을 제안하고, 기록을 선택한 경우에만 상세정보 확인·승인 흐름으로 들어간다.
- 배치 그래프의 승인 기록은 조사 필수 항목 확인과 근거 연결을 거쳐 작성한다.

## ANTI-PATTERNS

- CLI 프로토타입 수정만으로 `backend/` 서비스 동작이 바뀐다고 가정하지 않는다.
- 사례에서 찾은 원인을 확정 인과관계로 쓰지 않는다. `report.py`는 이를 우선 확인 가설로 기록한다.
- 기록 저장을 `cli.py`의 승인 확인 이전으로 이동하지 않는다.
- `tests/test_workflow.py`를 백엔드 DB/API 검증으로 간주하지 않는다.
