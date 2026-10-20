# 시스템 아키텍처

## 1. 역할

| 역할 | 하는 일 |
|---|---|
| 작업자 `worker` | 이상 현상 입력 → 조사 요청, 내 요청 결과 확인 |
| 공정 엔지니어 `engineer` | 진행 관찰, 보고서·분류 검토 → 승인 / 수정 요청 (Human-in-the-loop) |
| 관리자 `admin` | 전체 조사 이력, 분류 비율, 도구 호출 지표, 색인 문서 |

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
| REST API | 인증(목업 헤더), 권한, 작업 생성, 이벤트 스트림 | 조사 로직 |
| LangGraph | 분류 → 분기 조사 → 보고서 → 승인 대기 | 수치 계산 |
| 조사 도구 | SQL 조회, 통계(z-score, 추세) 계산 | 문장 생성 |
| PostgreSQL | 데이터·벡터·작업 상태·그래프 체크포인트 | — |

## 3. 요청 흐름

```mermaid
sequenceDiagram
  autonumber
  actor W as 작업자
  actor E as 엔지니어
  participant FE as Frontend
  participant API as REST API
  participant G as LangGraph
  participant DB as PostgreSQL
  participant L as OpenAI

  W->>FE: 장비·run·증상 입력
  FE->>API: POST /api/ai/tasks
  API->>DB: tasks INSERT (QUEUED)
  API-->>FE: 202 { taskId }
  FE->>API: GET /api/ai/tasks/{id}/stream (SSE)
  API->>G: 백그라운드 실행
  G->>L: 분류 (장비 / 공정 / 불명확)
  G->>DB: 이벤트 CLASSIFIED
  loop 분기 서브그래프 (최대 8턴)
    G->>L: 다음 도구 선택
    G->>DB: 도구 실행 (조회·계산) + TOOL_START / TOOL_END
  end
  G->>G: verify_category (근거가 다른 분류면 1회 재분류)
  G->>L: 보고서 작성
  G->>DB: APPROVAL_REQUIRED, 체크포인트 저장 후 정지
  API-->>FE: SSE 이벤트 실시간 전달
  E->>FE: 보고서 검토
  alt 수정 요청 / 분류 정정
    FE->>API: POST /approval { action: revise }
    API->>G: 같은 thread_id 로 재개 → 재작성 → 다시 APPROVAL_REQUIRED
  else 승인
    FE->>API: POST /approval { action: approve }
    API->>G: 재개 → investigations 저장
    G->>DB: DONE
  end
```

## 4. 작업 상태

```mermaid
stateDiagram-v2
  [*] --> QUEUED: POST /tasks
  QUEUED --> RUNNING: 그래프 시작
  RUNNING --> WAITING_APPROVAL: 보고서 완성
  WAITING_APPROVAL --> RUNNING: 수정 요청 / 승인
  RUNNING --> DONE: 저장 완료 또는 근거 부족 종료
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
