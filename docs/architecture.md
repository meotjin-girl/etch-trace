# 시스템 아키텍처

## 1. 역할

| 역할 | 하는 일 |
|---|---|
| 작업자 `worker` | 채팅으로 이상 현상 신고, 재질문에 답변, 내 요청 진행·결과 확인 |
| 장비 엔지니어 `engineer` · specialty `EQUIPMENT` | **배정된** 장비 이상 건만 보고 검토 → 승인 / 수정 / 분류 정정 |
| 공정 엔지니어 `engineer` · specialty `PROCESS` | **배정된** 공정 이상 건만 보고 검토 → 승인 / 수정 / 분류 정정 |
| 관리자 `admin` | 전체 조사 이력, 분류 비율, 엔지니어별 부하, 미배정 건 수동 배정 |

엔지니어는 역할이 하나(`engineer`)이고 전문 분야(`specialty`)와 담당 장비로 구분한다. 배정·접근 규칙은 [agent.md 3장](agent.md#3-담당-엔지니어-배정과-접근-범위).

## 2. 구성도

실선은 오늘 구현, 점선은 다음 단계.

```mermaid
flowchart LR
  FE["Frontend<br/>frontend/ (정적 HTML·JS)"]
  subgraph EC2["EC2 · docker compose"]
    NG["nginx :80"]
    subgraph AG["agent (FastAPI)"]
      API["REST API · SSE<br/>main.py"]
      GR["LangGraph<br/>graph.py · branches.py"]
      TL["조사 도구<br/>tools.py"]
    end
    PG[("PostgreSQL + pgvector<br/>공정 데이터 · 문서 벡터<br/>작업 · 이벤트 · 체크포인트")]
  end
  LLM["OpenAI<br/>gpt-5.4-mini"]
  FE -- "REST / SSE" --> NG --> API
  API -- "백그라운드 실행" --> GR --> TL --> PG
  API -- "task_events 조회" --> PG
  GR -- "분류 · 도구 선택 · 보고서" --> LLM
  TL -- "임베딩" --> LLM
  SB["Spring Boot 게이트웨이"] -.-> API
  KF["Kafka 대기열"] -.-> GR
  MCP["MCP 서버<br/>business / rag"] -.-> TL
```

| 구성 요소 | 책임 | 하지 않는 것 |
|---|---|---|
| Frontend | 화면, 역할별 라우팅 | DB 직접 접근, 판정 로직 |
| nginx | 단일 공개 포트, SSE 프록시 | 비즈니스 로직 |
| REST API | 인증(목업 헤더), **배정 기반 접근 제한**, 작업 생성, 대화 답변, 이벤트 스트림 | 조사 로직 |
| LangGraph | 정보 추출·재질문 → 분류 → 배정 → 분기 조사 → 보고서 → 승인 대기 | 수치 계산, 권한 검사 |
| 조사 도구 | SQL 조회, 통계(z-score, 추세) 계산 | 문장 생성 |
| PostgreSQL | 데이터·벡터·작업 상태·그래프 체크포인트 | — |

## 3. 요청 흐름

```mermaid
sequenceDiagram
  autonumber
  actor W as 작업자
  actor E as 배정 엔지니어
  participant FE as Frontend
  participant API as REST API
  participant G as LangGraph
  participant DB as PostgreSQL
  participant L as OpenAI

  W->>FE: 채팅으로 이상 현상 입력
  FE->>API: POST /api/ai/tasks { question }
  API->>DB: tasks INSERT (QUEUED)
  API-->>FE: 202 { taskId }
  FE->>API: GET /api/ai/tasks/{id}/stream (SSE)
  API->>G: 백그라운드 실행
  G->>L: intake (장비 · run · 증상 추출)
  opt 정보 부족
    G->>DB: QUESTION, 체크포인트 저장 후 정지 (WAITING_INPUT)
    API-->>FE: 봇 재질문
    W->>FE: 답변
    FE->>API: POST /messages { text }
    API->>G: 같은 thread_id 로 재개
  end
  G->>L: 분류 (장비 / 공정 / 불명확)
  G->>DB: CLASSIFIED, assignee 저장 + ASSIGNED
  Note over E,API: 이 시점부터 배정 엔지니어에게만 작업이 보인다
  loop 분기 서브그래프 (최대 8턴)
    G->>L: 다음 도구 선택
    G->>DB: 도구 실행 (조회·계산) + TOOL_START / TOOL_END
  end
  G->>G: verify_category (분류 바뀌면 재배정)
  G->>L: 보고서 작성
  G->>DB: APPROVAL_REQUIRED, 체크포인트 저장 후 정지
  API-->>FE: 요청자: "검토 중" / 배정 엔지니어: 승인 카드
  E->>FE: 보고서 검토
  alt 수정 요청
    FE->>API: POST /approval { revise }
    API->>G: 재개 → 재작성 → 다시 APPROVAL_REQUIRED
  else 분류 정정
    FE->>API: POST /approval { revise, category }
    API->>G: 재개 → 해당 분기 조사 → 다른 분야 엔지니어로 재배정
  else 승인
    FE->>API: POST /approval { approve }
    API->>G: 재개 → investigations 저장
    G->>DB: DONE
  end
```

## 4. 작업 상태

```mermaid
stateDiagram-v2
  [*] --> QUEUED: POST /tasks
  QUEUED --> RUNNING: 그래프 시작
  RUNNING --> WAITING_INPUT: 정보 부족 · 재질문
  WAITING_INPUT --> RUNNING: POST /messages
  RUNNING --> WAITING_APPROVAL: 보고서 완성
  WAITING_APPROVAL --> RUNNING: 수정 요청 / 분류 정정 / 승인
  RUNNING --> DONE: 저장 완료 또는 근거·정보 부족 종료
  RUNNING --> FAILED: 예외
  DONE --> [*]
  FAILED --> [*]
```

## 5. 배포

| 서비스 | 포트 | 외부 공개 |
|---|---|---|
| nginx | 80 | O (보안그룹 HTTP 80) |
| agent | 8000 | X (docker network 내부) |
| postgres | 5432 | X |

## 6. 데이터 (PHM 2018 이온 밀 식각)

- 조사 단위 `run_id = {runnum}-{Lot}` (run 하나 = 레시피 하나). 현재 장비 `01M01` 적재: run 11,475 / 고장 19.
- 센서값은 표준화되어 **단위 없음**. 고장 시각은 정비 **정지 시각**(발생 시각 아님).
- 고장 3종이 모두 FlowCool 계열 → 장비 이상 분기의 정답 사례로 쓸 수 있음.
- 장비가 1대뿐이라 "같은 레시피를 다른 장비에서 돌려도 이상한가" 비교는 장비 추가 적재 후 가능.
