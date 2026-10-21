# sop-ocap/ — 식각 SOP·OCAP 문서

이 폴더에는 식각 SOP 3종, OCAP 19종과 작성 근거 조사 메모가 있습니다. 현재 TRACE 화면과 문서 MCP에는 이 폴더의 원문이 자동으로 연결되어 있지 않습니다.

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
| [OCAP-ETCH-RATE](OCAP-ETCH-RATE_식각속도이상.md) | OCAP | 식각 속도 이상 대응 | Etch공정기술팀 | etch rate·식각 깊이 이탈 |
| [OCAP-ETCH-UNI](OCAP-ETCH-UNI_식각균일도이상.md) | OCAP | 식각 균일도 이상 대응 | Etch공정기술팀 | wafer 내·wafer 간 균일도 이탈 |
| [OCAP-ETCH-DEF](OCAP-ETCH-DEF_표면결함이상.md) | OCAP | 파티클·스크래치·표면 결함 대응 | Etch공정기술팀 | defect 검사 이상 |
| [OCAP-ETCH-CD](OCAP-ETCH-CD_CD프로파일이상.md) | OCAP | CD·식각 프로파일 이상 대응 | Etch공정기술팀 | CD·profile·residue 이탈 |
| [OCAP-ETCH-PM](OCAP-ETCH-PM_정비이후이상.md) | OCAP | 정비·세정 이후 이상 대응 | Etch설비기술팀 | PM·부품 교체 이후 변화 |
| [OCAP-ETCH-VAC](OCAP-ETCH-VAC_진공이상.md) | OCAP | 진공 배기·기저 압력·누설 대응 | Etch설비기술팀 | base pressure·pump down·누설 이상 |
| [OCAP-ETCH-ARC](OCAP-ETCH-ARC_점화아크이상.md) | OCAP | 플라즈마 점화 실패·아크 대응 | Etch설비기술팀 | ignition failure·arc 인터락 |
| [OCAP-ETCH-BEAM](OCAP-ETCH-BEAM_이온빔이상.md) | OCAP | 이온 빔 전압·전류 이상 대응 | Etch설비기술팀 | Ion Mill beam 이상 |
| [OCAP-ETCH-GRID](OCAP-ETCH-GRID_그리드이상.md) | OCAP | Suppressor·이온 소스 그리드 이상 대응 | Etch설비기술팀 | suppressor·grid 이상 |
| [OCAP-ETCH-MOTION](OCAP-ETCH-MOTION_웨이퍼구동이상.md) | OCAP | 웨이퍼 회전·기울기·고정구 이상 대응 | Etch설비기술팀 | Ion Mill motion 이상 |
| [OCAP-ETCH-ESC](OCAP-ETCH-ESC_정전척이상.md) | OCAP | 정전척 흡착·Dechuck 이상 대응 | Etch설비기술팀 | ESC·chuck/dechuck 이상 |
| [OCAP-ETCH-OES](OCAP-ETCH-OES_발광신호이상.md) | OCAP | 플라즈마 발광 신호 이상 대응 | Etch공정기술팀 | OES 신호 이상 |
| [OCAP-ETCH-SHT](OCAP-ETCH-SHT_ShutterPBN이상.md) | OCAP | Shutter·PBN 이상 대응 | Etch설비기술팀 | Ion Mill shutter·PBN 이상 |
| [OCAP-ETCH-STEP](OCAP-ETCH-STEP_공정시퀀스이상.md) | OCAP | 공정 Step 지속 시간·시퀀스 이상 대응 | Etch공정기술팀 | timeout·sequence error |

[00_식각공정_조사.md](00_식각공정_조사.md)는 작성 근거를 모은 조사 메모입니다.

## TRACE 연동 상태

| 위치 | 현재 내용 |
| --- | --- |
| `sop-ocap/` | 위 SOP 3종, OCAP 19종 및 조사 메모 |
| `frontend/sop-data.js` | SOP 화면용 시연 문서 3종을 코드에 포함. 이 폴더의 원문은 표시하지 않음 |
| `db/documents.json` → 문서 MCP | 시연용 조항 5건을 DB에 적재하고 ID로 조회. 이 폴더의 원문은 적재하지 않음 |

아래 조항 ID 대응표는 연동 시 참고용입니다. 현재 시연 데이터와 이 폴더의 문서를 같은 원문으로 취급하지 않습니다.

## 문서 머리

메타데이터(frontmatter)는 쓰지 않습니다. 모든 SOP·OCAP 문서는 제목과 아래 표 하나로 시작합니다.

```markdown
# OCAP-ETCH-EPD Endpoint 지연·미검출 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.1 | 2026-10-20 |
```

| 항목 | 문서 위치 |
| --- | --- |
| 담당 팀 | 머리 표 `담당 팀` |
| 버전 | 머리 표 `버전` |
| 최근 개정 | 머리 표 `최근 개정` (YYYY-MM-DD) |

개정하면 머리 표의 버전·날짜를 바꾸고, 본문 끝 **8. 개정 이력** 표에 한 줄을 더합니다. 개정 이력 표는 `버전·날짜·내용(또는 변경 내용)`을 쓰며, 문서에 따라 `검토·승인` 열이 추가됩니다.

## 본문 구조

**SOP** — EPA QA/G-6 §4.1(기술 SOP)·§4.2(관리 SOP)의 구성을 따릅니다.

`1 목적 및 적용 범위 · 2 용어 · 3 역할과 책임 · 4 절차 · 5 판정 기준·검증 · 6 기록 관리 · 7 참고 문서 · 8 개정 이력`

**OCAP** — Activator·Checkpoint·Terminator 3요소와 반도체 OCAP 특허(US 12062558)의 순서 있는 점검 구조를 따릅니다. Checkpoint에는 `확인`, 관측된 `이상`, 아직 검증되지 않은 `원인 후보`, `추가 검증 또는 조치`를 필요한 만큼 씁니다. OCAP ID는 `OCAP-{공정}-{항목}`입니다.

`1 적용 범위 · 2 Activator · 3 즉시 조치 · 4 Checkpoints · 5 Terminator · 6 에스컬레이션 · 7 기록 항목 · 8 개정 이력`

각 OCAP의 적용 범위에는 `장비 유형`, `공정·감시 항목`, `필요 데이터`, `검증 가능 범위`를 씁니다. Activator는 가능한 경우 경고와 중대 이상을 나누고, 승인된 장비 알람·공정 스펙·통계 편차를 서로 구분합니다.

Checkpoint는 확인 순서를 제시하되 관측 사실만으로 원인을 확정하지 않습니다. `원인 후보`, 후보를 지지하거나 반박하는 근거, 미확인 사항과 추가 검증을 기록합니다. 현장 점검이나 승인된 정비 절차로 확인되기 전에는 `확인된 원인`으로 바꾸지 않습니다.

Terminator는 아래 세 결정을 분리합니다.

1. 조사 종결: 필요한 비교·원인 후보·미확인 사항·후속 조치가 기록됨
2. 장비 복귀: 계통별 복구 조건과 SOP-ETCH-01 §4.8 재인증을 통과하고 engineer가 승인함
3. Lot 처분: SOP-ETCH-20에 따라 별도로 Release·추가 계측·Rework·Scrap을 결정함

## 조항 ID 규칙

- 번호로 시작하는 제목(`## 4.` / `### 4.2`)이 조항입니다. 조항 ID는 `{문서 ID}#{번호}`입니다. 예: `SOP-ETCH-12#4.2`, `OCAP-ETCH-RF#4.3`
- 문서 MCP(`mcp/rag.py`)는 DB에 등록된 ID를 정확히 조회합니다. 이 폴더의 Markdown을 자동으로 읽지는 않습니다. 연동 후에는 기존 조항 번호를 유지합니다.
- `db/documents.json`의 기존 조항 문장은 새 조항의 첫 문장으로 그대로 옮겼습니다.

| 기존 조항 (documents.json) | 새 조항 |
| --- | --- |
| SOP-ETCH-12#4.2 | SOP-ETCH-12#4.2 (그대로) |
| WI-PM-07#3.1 | SOP-ETCH-01#4.6 |
| SPEC-RF-03#2.4 | OCAP-ETCH-RF#4.3 |
| WI-MFC-02#5.3 | OCAP-ETCH-PRS#4.3 |
| SPEC-EPD-01#6.2 | OCAP-ETCH-EPD#4.2 |

`db/documents.json`과 `db/cases.json`은 아직 기존 ID를 씁니다. 이 폴더의 문서를 연동할 때 위 표에 따라 조항 참조도 함께 갱신해야 합니다.

## 작성 규칙

- SOP 화면의 마크다운 렌더러는 일부 문법만 지원합니다. 중첩 목록, HTML, mermaid를 쓰지 않습니다. 표, 단일 단계 목록, 인용, 코드, 굵게는 됩니다.
- 문장은 짧은 단계형 능동문으로 씁니다 (EPA G-6 §1.4).
- 안전 경고는 해당 단계 바로 앞에 **경고:**로 씁니다 (EPA G-6 §4.1 d).
- 원인은 "확인 가설"로 쓰고 단정하지 않습니다.
- 표준화 값으로 수집되는 센서는 물리 단위 없이 z-score로만 씁니다. 고장 기록 시각은 장비 정지 시각입니다.
- 센서는 같은 recipe·step과 실제 운전 조건에서 비교하며 대상 시점 이후 데이터는 기준 run으로 쓰지 않습니다.
- 데이터가 없으면 추정값을 만들지 않고 `추가 데이터 필요` 또는 `현장 점검 필요`로 기록합니다.
- OCAP 간 이동 시 이동 사유와 출발·도착 조항 ID를 기록합니다.
- 안전·장비 조작은 사업장과 제조사의 승인된 절차가 이 문서보다 우선합니다.

## 근거 자료

- [EPA QA/G-6 Guidance for Preparing Standard Operating Procedures (2001)](https://archive.epa.gov/region1/lab/web/pdf/g6-final.pdf): 표지 항목(§3.1), 문서 관리 표기(§2.5), 검토·승인(§2.2), 개정(§2.3), 기술·관리 SOP 구성(§4.1, §4.2)
- [US 12062558 B2](https://patents.google.com/patent/US12062558): 반도체 OCAP. 공정 단계+항목 OCAPID, 순서 있는 점검 항목과 원인 분류·조치, MES hold/release 연동
- [Montgomery, Introduction to Statistical Quality Control, Ch.5 OCAP (강의 자료)](https://elearning.uniparthenope.it/mod/resource/view.php?id=23371): Activator·Checkpoint·Terminator
- [INFICON — SEMI E10 장비 상태](https://www.inficon.com/en/news/what-do-we-mean-when-we-refer-to-tool-availability)
