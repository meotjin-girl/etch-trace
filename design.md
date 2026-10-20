# TRACE Design System

> 식각 공정 이상 조사 Agent **TRACE**의 디자인 기준 문서.
> 화면 적용은 API 명세서와 와이어프레임이 확정된 뒤 진행한다.

| 항목 | 내용 |
|---|---|
| 버전 | v0.1 (초안) |
| 최종 수정 | YYYY-MM-DD |
| 작성 | |

---

## 1. 디자인 원칙

1.
2.
3.

---

## 2. Foundations

### 2.1 Color

**기본 팔레트**

| 토큰 | 값 | 용도 |
|---|---|---|
| `color.primary` | | |
| `color.surface` | | |
| `color.text` | | |
| `color.border` | | |

**의미 색** — API 값과 1:1로 매핑한다.

| 구분 | 값 (API) | 토큰 | 색 |
|---|---|---|---|
| 작업 상태 | `QUEUED` · `RUNNING` | | |
| | `WAITING_INPUT` · `WAITING_APPROVAL` | | |
| | `DONE` | | |
| | `FAILED` | | |
| 분류 | `EQUIPMENT` · `PROCESS` · `UNCLEAR` | | |
| 편차 강도 | \|z\| 2~3 경미 · \|z\| ≥ 3 확인 필요 | | |

### 2.2 Typography

| 토큰 | 글꼴 | 크기 / 행간 | 굵기 | 용도 |
|---|---|---|---|---|
| `type.title` | | | | |
| `type.body` | | | | |
| `type.caption` | | | | |
| `type.mono` | | | | run_id · 수치 · 코드 |

### 2.3 Spacing · Radius · Elevation

| 토큰 | 값 | 용도 |
|---|---|---|
| `space.*` | | |
| `radius.*` | | |
| `shadow.*` | | |

### 2.4 Layout

- 기준 해상도 / 그리드:
- 브레이크포인트:

---

## 3. Components

API 응답 · SSE 이벤트와 연결되는 핵심 컴포넌트. 명세는 와이어프레임 확정 후 채운다.

| 컴포넌트 | 용도 | 연결 데이터 (API · 이벤트) | 상태 · 변형 |
|---|---|---|---|
| 상태 배지 | 작업 진행 상태 | `status` | |
| 분류 배지 | 장비 / 공정 / 불명확 | `category` | |
| 채팅 메시지 | 접수 대화 · 재질문 | `QUESTION` · `USER_MESSAGE` | |
| 진행 타임라인 | 에이전트 단계 · 도구 호출 | `PLAN` · `TOOL_START` · `TOOL_END` | |
| 근거 패널 | 수치 근거 · 문서 출처 | `TOOL_END.result` · `report.evidence` | |
| 보고서 카드 | 요약 · 사실 · 다음 조치 · 미확인 | `report` | |
| 승인 카드 | 승인 · 수정 요청 · 분류 정정 | `APPROVAL_REQUIRED` · `POST /approval` | |

---

## 4. 화면 적용

와이어프레임 확정 후 작성.

| 화면 | 역할 | 와이어프레임 | 사용 API | 사용 컴포넌트 |
|---|---|---|---|---|
| | 작업자 | | | |
| | 엔지니어 | | | |
| | 관리자 | | | |

---

## 5. References

| # | 링크 | 참고 포인트 |
|---|---|---|
| 1 | | |

---

## 6. 변경 이력

| 날짜 | 버전 | 내용 |
|---|---|---|
| | v0.1 | 초안 |
