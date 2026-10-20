# sop/ — 식각 SOP·OCAP 문서

TRACE 조사 Agent가 근거로 인용하고 SOP 화면에 표시하는 문서입니다.

## 문서 목록

| ID | 유형 | 제목 | 담당 팀 | 언제 여는가 |
| --- | --- | --- | --- | --- |
| [SOP-ETCH-01](SOP-ETCH-01_식각설비운영.md) | SOP | 식각 설비 운영 | Etch설비기술팀 | 정상 운전, 일상 점검, PM, 생산 복귀 |
| [SOP-ETCH-12](SOP-ETCH-12_식각이상대응.md) | SOP | 식각 장비 이상 대응 | Etch공정기술팀 | 모든 이상 조사의 공통 흐름 |
| [SOP-ETCH-20](SOP-ETCH-20_LotHoldRelease.md) | SOP | Lot Hold/Release | Etch공정기술팀 | 영향 lot 보류, 처분, 해제 승인 |
| [OCAP-ETCH-PRS](OCAP-ETCH-PRS_챔버압력이상.md) | OCAP | 챔버 압력 이상 대응 | Etch설비기술팀 | 압력·throttle valve 이탈 |
| [OCAP-ETCH-GAS](OCAP-ETCH-GAS_가스유량이상.md) | OCAP | 가스 유량 이상 대응 | Etch설비기술팀 | MFC readback 이탈 |
| [OCAP-ETCH-TMP](OCAP-ETCH-TMP_온도냉각이상.md) | OCAP | 온도·후면 냉각 이상 대응 | Etch설비기술팀 | He 후면 냉각, FlowCool |
| [OCAP-ETCH-RF](OCAP-ETCH-RF_RF반사전력이상.md) | OCAP | RF 반사전력 이상 대응 | Etch설비기술팀 | reflected power 상승 |
| [OCAP-ETCH-EPD](OCAP-ETCH-EPD_Endpoint이상.md) | OCAP | Endpoint 지연·미검출 대응 | Etch공정기술팀 | endpoint 지연, timeout |

[00_식각공정_조사.md](00_식각공정_조사.md)는 작성 근거를 모은 조사 메모입니다.

## 문서 머리

메타데이터(frontmatter)는 쓰지 않습니다. 모든 문서는 제목과 아래 표 하나로 시작합니다. SOP 화면에 표시되는 항목이 이 세 가지입니다.

```markdown
# OCAP-ETCH-EPD Endpoint 지연·미검출 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.0 | 2026-10-20 |
```

| 화면 항목 | 문서 위치 |
| --- | --- |
| 담당 팀 | 머리 표 `담당 팀` |
| 버전 | 머리 표 `버전` |
| 최근 개정 | 머리 표 `최근 개정` (YYYY-MM-DD) |

개정하면 머리 표의 버전·날짜를 바꾸고, 본문 끝 **8. 개정 이력** 표에 한 줄을 더합니다.

## 본문 구조

**SOP** — EPA QA/G-6 §4.1(기술 SOP)·§4.2(관리 SOP)의 구성을 따릅니다.

`1 목적 및 적용 범위 · 2 용어 · 3 역할과 책임 · 4 절차 · 5 판정 기준·검증 · 6 기록 관리 · 7 참고 문서 · 8 개정 이력`

**OCAP** — Activator·Checkpoint·Terminator 3요소와 반도체 OCAP 특허(US 12062558)의 "순서 있는 점검 항목 → 원인 분류 → 조치" 구조를 따릅니다. 각 Checkpoint는 `확인 / 이상 판정 / 원인 분류 / 조치` 네 줄로 씁니다. OCAP ID는 `OCAP-{공정}-{항목}`입니다.

`1 적용 범위 · 2 Activator · 3 즉시 조치 · 4 Checkpoints · 5 Terminator · 6 에스컬레이션 · 7 기록 항목 · 8 개정 이력`

## 조항 ID 규칙

- 번호로 시작하는 제목(`## 4.` / `### 4.2`)이 조항입니다. 조항 ID는 `{문서 ID}#{번호}`입니다. 예: `SOP-ETCH-12#4.2`, `OCAP-ETCH-RF#4.3`
- 문서 MCP(`mcp/rag.py`)는 이 ID로 정확히 조회합니다. 개정할 때 기존 조항 번호를 바꾸지 않습니다.
- `db/documents.json`의 기존 조항 문장은 새 조항의 첫 문장으로 그대로 옮겼습니다.

| 기존 조항 (documents.json) | 새 조항 |
| --- | --- |
| SOP-ETCH-12#4.2 | SOP-ETCH-12#4.2 (그대로) |
| WI-PM-07#3.1 | SOP-ETCH-01#4.6 |
| SPEC-RF-03#2.4 | OCAP-ETCH-RF#4.3 |
| WI-MFC-02#5.3 | OCAP-ETCH-PRS#4.3 |
| SPEC-EPD-01#6.2 | OCAP-ETCH-EPD#4.2 |

`db/documents.json`과 `db/cases.json`은 아직 기존 ID를 씁니다. seed를 이 폴더 기준으로 바꿀 때 위 표대로 옮깁니다.

## 작성 규칙

- SOP 화면의 마크다운 렌더러는 일부 문법만 지원합니다. 중첩 목록, HTML, mermaid를 쓰지 않습니다. 표, 단일 단계 목록, 인용, 코드, 굵게는 됩니다.
- 문장은 짧은 단계형 능동문으로 씁니다 (EPA G-6 §1.4).
- 안전 경고는 해당 단계 바로 앞에 **경고:**로 씁니다 (EPA G-6 §4.1 d).
- 원인은 "확인 가설"로 쓰고 단정하지 않습니다.
- 표준화 값으로 수집되는 센서는 물리 단위 없이 z-score로만 씁니다. 고장 기록 시각은 장비 정지 시각입니다.

## 근거 자료

- [EPA QA/G-6 Guidance for Preparing Standard Operating Procedures (2001)](https://archive.epa.gov/region1/lab/web/pdf/g6-final.pdf): 표지 항목(§3.1), 문서 관리 표기(§2.5), 검토·승인(§2.2), 개정(§2.3), 기술·관리 SOP 구성(§4.1, §4.2)
- [US 12062558 B2](https://patents.google.com/patent/US12062558): 반도체 OCAP. 공정 단계+항목 OCAPID, 순서 있는 점검 항목과 원인 분류·조치, MES hold/release 연동
- [Montgomery, Introduction to Statistical Quality Control, Ch.5 OCAP (강의 자료)](https://elearning.uniparthenope.it/mod/resource/view.php?id=23371): Activator·Checkpoint·Terminator
- [INFICON — SEMI E10 장비 상태](https://www.inficon.com/en/news/what-do-we-mean-when-we-refer-to-tool-availability)
