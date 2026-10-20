# TRACE Design System

> 식각 공정 이상 조사 Agent **TRACE**의 디자인 기준 문서.
> 화면 적용은 API 명세서와 와이어프레임이 확정된 뒤 진행한다.

| 항목 | 내용 |
|---|---|
| 버전 | v0.3 (메인 레퍼런스 반영) |
| 최종 수정 | 2026-10-20 |
| 방향 | **Quiet Instrument** — NVIDIA의 정밀한 뼈대 + Linear · Warp의 따뜻한 다크 + xAI의 mono 라벨, 색은 산업 HMI처럼 이상 상태에만 |
| 레퍼런스 | [`references/`](references/README.md) |

---

## 1. 디자인 원칙

1. **평소엔 무채색, 색은 의미에만** — 화면의 90% 이상은 회색 계열. 색은 작업 상태 · 편차 강도 · AI 표시 · 사람의 결정에만 쓴다. ([ISA-101](references/11-isa-101-hmi.md))
2. **계측기처럼 정밀하게** — 모든 면은 2px 모서리, 얇은 구분선 격자, 그림자 없음. 소비자 앱의 둥근 친근함 대신 엔지니어링 문서의 정확함. ([NVIDIA](references/01-nvidia.md))
3. **선보다 면으로 구조를 만든다** — 구분선 대비는 낮게, 영역은 면의 명도 차이로. 내비게이션은 한 단계 눌러 본문을 앞세운다. ([Linear](references/02-linear.md))
4. **숫자가 주인공** — 수치 · run_id는 mono + `tabular-nums`, 원천 ID를 옆에 붙인다. 메타 정보는 mono 대문자 라벨로 계측기처럼 표기한다. ([xAI · SpaceX](references/04-xai-spacex.md))
5. **AI는 표시하되 꾸미지 않는다** — AI 결과에는 `AI 초안` 라벨, 라벨에서 근거로 연결. 그라데이션 · 글로우 금지. ([Carbon for AI](references/14-carbon-for-ai.md))
6. **사람의 결정이 가장 선명하다** — 화면당 채워진 버튼(primary)은 하나. 승인 권한이 사람에게 있음을 위계로 보여준다. ([SAP AI](references/17-sap-ai-guidelines.md))

**하지 않는 것** — 블러 · 반투명(glass), 네온 다크 대시보드, 무지개색 차트, 둥근 pill 버튼, 촘촘한 목록의 카드 남발, 넓은 면의 순백 · 순흑, 채도 강한 브랜드 강조색.

---

## 2. Foundations

### 2.1 Color

라이트는 따뜻한 회색 종이 위 얇은 격자(NVIDIA · Linear 2026), 다크는 순흑 대신 따뜻한 차콜 면 계단(Warp · Linear). 괄호는 WCAG 대비 (라이트 · 다크).

**중립색**

| 토큰 | Light | Dark | 용도 |
|---|---|---|---|
| `color.canvas` | `#F7F7F5` | `#161412` | 페이지 배경 |
| `color.surface` | `#FFFFFF` | `#1D1A17` | 패널 · 표 · 입력 영역 |
| `color.surface-subtle` | `#EFEEEB` | `#25211D` | 사이드바 · 표 헤더 · hover |
| `color.line` | `#E6E5E1` | `#332E29` | 기본 구분선 (hairline) |
| `color.line-strong` | `#CFCEC9` | `#47413A` | 입력 테두리 · 보조 버튼 |
| `color.text-1` | `#1F1F1D` | `#F2EFE9` | 본문 · 제목 (15.4 · 15.1) |
| `color.text-2` | `#6B6A66` | `#B3AB9F` | 보조 텍스트 · 메타 라벨 (5.4 · 7.6) |
| `color.text-3` | `#8A8883` | `#857E74` | placeholder · 비활성만 (3.5 · 4.3) — 본문 금지 |

**포인트 색** — 클릭 가능한 요소와 승인 버튼에만. 채도를 낮춘 스틸 블루 하나.

| 토큰 | Light | Dark | 용도 |
|---|---|---|---|
| `color.action` | `#3D6A99` | `#7FA6CF` | primary 버튼 · 링크 · focus (5.7 · 6.8) |
| `color.on-action` | `#FFFFFF` | `#11161C` | action 위 텍스트 (5.7 · 7.2) |

**의미 색** — 배지는 `bg` + `text`, 수치 강조와 카드 마커는 `fg`.

| 토큰 | fg (L / D) | bg (L / D) | text (L / D) | 의미 |
|---|---|---|---|---|
| `color.normal` | `#3E7D5A` / `#6FB38A` | `#E4F0E8` / `#1E3227` | `#2C5E42` / `#8CC7A2` | 정상 · 완료 |
| `color.caution` | `#8F5F12` / `#D9A24A` | `#F6EBD6` / `#382B13` | `#7A4E0E` / `#E2B566` | 주의 · 사람 입력 대기 |
| `color.abnormal` | `#B83A3A` / `#E07A73` | `#F7E1E0` / `#3D1F1E` | `#8C2626` / `#EE9A93` | 이상 · 실패 |
| `color.ai` | `#6E62C4` / `#A398E8` | `#ECEAF8` / `#29253F` | `#463C99` / `#B7AEF0` | AI 생성 표시 전용 |

**API 값 매핑**

| 구분 | 값 (API) | 표현 |
|---|---|---|
| 작업 상태 | `QUEUED` | 중립 배지 |
| | `RUNNING` | 중립 배지 + 진행 표시 |
| | `WAITING_INPUT` · `WAITING_APPROVAL` | `caution` 배지 — 사람이 움직여야 하는 상태 |
| | `DONE` | `normal` 배지 |
| | `FAILED` | `abnormal` 배지 |
| 분류 | `EQUIPMENT` · `PROCESS` · `UNCLEAR` | **중립 배지** (라벨로 구분, 경보가 아니므로 색 없음) |
| 편차 강도 | \|z\| < 2 | 기본 텍스트 |
| | 2 ≤ \|z\| < 3 경미한 편차 | `caution.fg` 수치 |
| | \|z\| ≥ 3 확인 필요 편차 | `abnormal.fg` 수치 |
| AI | 보고서 · 요약 · 분류 근거 | `ai` 라벨 (`AI 초안`) |

### 2.2 Typography

| 토큰 | 글꼴 | 크기 / 행간 | 굵기 | 자간 | 용도 |
|---|---|---|---|---|---|
| `type.stat` | Pretendard | 32 / 36 | 600 | -0.02em | 관리자 KPI 숫자 ([ClickHouse](references/06-clickhouse.md)) |
| `type.title` | Pretendard | 20 / 28 | 600 | -0.01em | 화면 제목 |
| `type.heading` | Pretendard | 16 / 24 | 600 | 0 | 섹션 · 카드 제목 |
| `type.body` | Pretendard | 14 / 22 | 400 | 0 | 본문 · 보고서 |
| `type.label` | Pretendard | 13 / 20 | 500 | 0 | 버튼 · 표 헤더 · 폼 라벨 |
| `type.caption` | Pretendard | 12 / 16 | 400 | 0 | 보조 설명 · 시각 |
| `type.mono` | JetBrains Mono | 13 / 20 | 400 | 0 | run_id · 수치 · 도구명 · 코드 |
| `type.meta` | JetBrains Mono | 11 / 16 | 500 | 0.08em · **대문자** | 메타 라벨 (`RUN` · `STEP` · `TOOL` · `TURN 3/8`), `text-2` 색 |

- 수치 열은 `font-variant-numeric: tabular-nums`, 오른쪽 정렬
- 굵기는 400 · 500 · 600 세 단계만
- `type.meta`는 영문 · 숫자 라벨에만 쓴다 (한글은 대문자 개념이 없으므로 `type.caption`)

### 2.3 Shape · Spacing · Elevation · Motion

**Shape** — 각진 정밀함 ([NVIDIA](references/01-nvidia.md) · [IBM](references/05-ibm.md))

| 토큰 | 값 | 용도 |
|---|---|---|
| `radius.none` | 0 | 표 셀 · 구분선 · 전체 폭 띠 |
| `radius.xs` | 2 | **기본값** — 버튼 · 입력 · 배지 · 카드 · 패널 |
| `radius.sm` | 4 | 떠 있는 요소만 — 팝오버 · 모달 · 토스트 |
| `marker` | 6×6 정사각형 | 카드 좌상단 모서리 마커, 색 = 카드의 의미 색 (2.4 참고) |

pill(완전한 둥근 버튼)은 쓰지 않는다.

**Spacing** — `space.1`~`space.8` = 4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 (4px 기준)

**Elevation**

| 모드 | 방식 |
|---|---|
| Light | 그림자 없음. `canvas` 위 `surface` + `line` 1px로 구분 |
| Dark | 그림자 없음. `canvas` → `surface` → `surface-subtle` 면 계단으로 구분 ([Linear](references/02-linear.md)) |
| 공통 | 떠 있는 요소만 `shadow.popover` = `0 4px 16px rgb(0 0 0 / 8%)` (다크 24%) |

**Motion** — `motion.fast` 150ms ease-out(상태 변화 · hover), `motion.base` 200ms ease-out(패널 · SSE 진행 표시). 장식용 애니메이션 없음, `prefers-reduced-motion`이면 끔.

### 2.4 Layout · Density

- 데스크톱 우선, 최소 1280px · 12열 그리드 · 좌측 내비게이션 240px (`surface-subtle`로 한 단계 눌림)
- 정보는 구분선 격자로 다열 배치, 장식적 여백 · 일러스트 없음
- 테마: **라이트 기본**, 다크는 관리자 · 모니터링용 옵션

| 밀도 | 표 행 높이 | 컨트롤 높이 | 사용 화면 |
|---|---|---|---|
| compact | 32px | 28px | 엔지니어 검토 · 관리자 |
| comfortable | 40px | 36px | 작업자 채팅 · 로그인 |

**카드 마커 규칙** — 마커는 사람이 봐야 할 카드에만 붙인다.

| 카드 상태 | 마커 색 |
|---|---|
| 승인 대기 · 재질문 대기 | `caution.fg` |
| AI 초안 보고서 | `ai.fg` |
| 실패 · 확인 필요 편차 포함 | `abnormal.fg` |
| 그 외 | 마커 없음 |

---

## 3. Components

API 응답 · SSE 이벤트와 연결되는 핵심 컴포넌트. 상세 명세는 와이어프레임 확정 후 채운다.

| 컴포넌트 | 용도 | 연결 데이터 (API · 이벤트) | 규칙 |
|---|---|---|---|
| 상태 배지 | 작업 진행 상태 | `status` | 2.1 API 값 매핑, `radius.xs` |
| 분류 배지 | 장비 / 공정 / 불명확 | `category` | 중립색, 라벨로만 구분 |
| 메타 라벨 | run · step · 도구 · 턴 | `run_id` · `PLAN.turn` · `TOOL_*.name` | `type.meta` 대문자 mono |
| 채팅 메시지 | 접수 대화 · 재질문 | `QUESTION` · `USER_MESSAGE` | 재질문은 빠진 항목(`missing`)을 칩으로 표시 |
| 진행 타임라인 | 에이전트 단계 · 도구 호출 | `PLAN` · `TOOL_START` · `TOOL_END` | 도구 결과는 기본 접힘, 소요 ms는 `type.mono`, 실패만 `abnormal` |
| 근거 패널 | 수치 근거 · 문서 출처 | `TOOL_END.result` · `report.evidence` | compact 표, 구분선 격자, 수치 mono · 원천 run_id 표기 |
| 보고서 카드 | 요약 · 사실 · 다음 조치 · 미확인 | `report` | `ai` 마커 + `AI 초안` 라벨 → 근거 패널 연결 |
| 승인 카드 | 승인 · 수정 요청 · 분류 정정 | `APPROVAL_REQUIRED` · `POST /approval` | `caution` 마커, primary는 `승인` 하나 |
| 지표 타일 | 관리자 KPI | `GET /api/admin/overview` | `type.stat` 숫자 + `type.meta` 라벨, 그림자 없는 타일 |

---

## 4. 화면 적용

와이어프레임 확정 후 작성.

| 화면 | 역할 | 밀도 | 와이어프레임 | 사용 API | 사용 컴포넌트 |
|---|---|---|---|---|---|
| | 작업자 | comfortable | | | |
| | 엔지니어 | compact | | | |
| | 관리자 | compact | | | |

---

## 5. References

[`references/README.md`](references/README.md)

| 구분 | 레퍼런스 |
|---|---|
| **메인 — 시각 언어** | [NVIDIA](references/01-nvidia.md) (뼈대) · [Linear](references/02-linear.md) (다크 기준) · [Warp](references/03-warp.md) (다크 톤) · [xAI · SpaceX](references/04-xai-spacex.md) (메타 라벨) · [IBM](references/05-ibm.md) (타일) · [ClickHouse](references/06-clickhouse.md) (KPI) |
| 원칙 — 산업 · AI · 데이터 | [ISA-101](references/11-isa-101-hmi.md) · [Siemens iX](references/12-siemens-ix.md) · [Vercel Geist](references/13-vercel-geist.md) · [Carbon for AI](references/14-carbon-for-ai.md) · [Blueprint](references/15-palantir-blueprint.md) · [Grafana Saga](references/16-grafana-saga.md) · [SAP AI](references/17-sap-ai-guidelines.md) |
| 원본 분석 | [`references/design-md/`](references/design-md/) — getdesign.md DESIGN.md 7종 |

---

## 6. 변경 이력

| 날짜 | 버전 | 내용 |
|---|---|---|
| 2026-10-20 | v0.1 | 초안 |
| 2026-10-20 | v0.2 | 방향 Quiet Instrument 확정, 원칙 · 색 · 타이포 · 간격 · 밀도 토큰 초안, references 연결 |
| 2026-10-20 | v0.3 | getdesign.md 메인 레퍼런스 반영 — radius 2px 기본, 따뜻한 차콜 다크, `type.meta` · `type.stat`, 카드 마커 규칙, 지표 타일 |
