# 식각 장비 이상 조사 LangGraph Agent

특정 식각 장비 이상에 대한 질문을 받아 관련 문서와 과거 사례를 찾고, 부족한 정보를 재질문한 뒤 근거가 연결된 답변을 제공하는 LangGraph 서비스입니다. 사용자가 원할 때만 답변을 승인용 조사 기록으로 전환합니다.

## 흐름

```text
사용자 질문 → 조건 추출 ──(부족)──> 재질문
                  │
                  └─> 과거 사례·문서 검색 → 수치 분석 → 근거 기반 답변
                                                       │
                                     기록 불필요 ──────┴─> 종료
                                                       │
                                     기록 필요 → 정보 보완 → 작성 → 승인
```

- 재질문과 승인에는 LangGraph `interrupt()`/`Command(resume=...)`를 사용합니다.
- 유사 사례는 장비, 챔버, 레시피, 제품, 증상, 공통 계측 항목별 점수와 이유를 함께 반환합니다.
- 현재값을 비교 사례 평균·표준편차와 비교해 차이율과 z-score를 계산합니다.
- 모든 수치 판단에는 원천 사례 ID, 원인/조치에는 문서 조항을 연결합니다.
- 과거 사례의 원인은 확정 원인이 아닌 “우선 확인 가설”로 표시합니다.

## 대화형 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
etch-investigate
```

실행 후 자연어로 질문합니다.

```text
나: ETCH-07 CH-B의 OX-120 공정에서 endpoint가 118초로 지연됐어.
    과거 유사 사례와 먼저 점검할 항목을 알려줘.
```

한 줄로 질문을 전달할 수도 있습니다.

```bash
etch-investigate --question "ETCH-07 CH-B의 endpoint가 118초로 지연됐어"
```

답변 후 승인용 조사 기록 작성 여부를 묻습니다. 작성하지 않으면 질의응답으로 종료하고, 작성하면 부족한 기록 항목을 재질문한 뒤 검토·승인 과정을 진행합니다. `--output` 뒤의 파일명을 생략하면 승인된 기록은 `investigation_report.md`에 저장됩니다.

JSON 입력은 대화 화면이 아닌 배치 자동화와 회귀 테스트를 위해 계속 지원합니다.

```bash
etch-investigate examples/request_complete.json --output investigation_report.md
```

## 테스트

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 실환경 연결 지점

`InvestigationRepository`는 현재 JSON 샘플을 읽습니다. 생산 적용 시 이 어댑터를 MES/FDC/APC, 정비 이력 DB, EDMS 문서 검색으로 교체하면 그래프와 승인 흐름은 그대로 유지할 수 있습니다. 운영 환경에서는 인메모리 체크포인터 대신 PostgreSQL 기반 체크포인터를 사용하고, 원본 로그 해시·문서 버전·사용자 인증·승인 전자서명을 추가해야 합니다.

LangGraph의 interrupt와 체크포인트 방식은 [공식 문서](https://docs.langchain.com/oss/python/langgraph/interrupts)를 기준으로 구성했습니다.
