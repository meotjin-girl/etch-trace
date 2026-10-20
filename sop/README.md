# sop/ — 식각 SOP·OCAP 문서

TRACE 조사 Agent가 근거로 인용하고 프론트엔드 SOP 화면에 표시할 문서입니다. 팹에서 시행 중인 문서라고 가정해 메타데이터를 채웠지만, **실제로는 시연용 샘플이며 공정 전문가 검토 전**입니다. `[예시]` 수치는 확정 전에는 판정에 쓰지 않습니다.

## 문서 목록

| ID | 유형 | 제목 | 언제 여는가 |
| --- | --- | --- | --- |
| [SOP-ETCH-01](SOP-ETCH-01_식각설비운영.md) | SOP | 식각 설비 운영 | 정상 운전, 일상 점검, PM, 생산 복귀 |
| [SOP-ETCH-12](SOP-ETCH-12_식각이상대응.md) | SOP | 식각 장비 이상 대응 | 모든 이상 조사의 공통 흐름 (범위 → 같은 조건 비교 → 교차 확인 → 이력 → 원인 후보) |
| [SOP-ETCH-20](SOP-ETCH-20_LotHoldRelease.md) | SOP | Lot Hold/Release | 영향 lot 보류, 처분, 해제 승인 |
| [OCAP-ETCH-PRS](OCAP-ETCH-PRS_챔버압력이상.md) | OCAP | 챔버 압력 이상 | 압력·throttle valve 이탈 |
| [OCAP-ETCH-GAS](OCAP-ETCH-GAS_가스유량이상.md) | OCAP | 가스 유량 이상 | MFC readback 이탈 |
| [OCAP-ETCH-TMP](OCAP-ETCH-TMP_온도냉각이상.md) | OCAP | 온도·후면 냉각 이상 | He 후면 냉각, FlowCool(PHM) |
| [OCAP-ETCH-RF](OCAP-ETCH-RF_RF반사전력이상.md) | OCAP | RF 반사전력 이상 | reflected power 상승 |
| [OCAP-ETCH-EPD](OCAP-ETCH-EPD_Endpoint이상.md) | OCAP | Endpoint 지연·미검출 | endpoint 지연, timeout |

[00_식각공정_조사.md](00_식각공정_조사.md)는 작성 근거를 모은 조사 메모이며, 관리 대상 문서가 아니라서 메타데이터가 없습니다.

## 메타데이터 (YAML frontmatter)

모든 SOP·OCAP 파일은 맨 앞에 한 단계짜리 YAML frontmatter를 둡니다. 중첩 객체는 쓰지 않습니다(Obsidian 속성 창과 프론트엔드에서 그대로 보이도록). `●`는 프론트엔드 [sop-data.js](../frontend/sop-data.js)가 이미 쓰는 필드입니다.

```yaml
---
id: OCAP-ETCH-EPD
title: Endpoint 지연·미검출 대응
category: 설비 알람 대응
version: "1.0"
status: 시행
owner: Etch공정기술팀
author: Etch공정기술팀 엔지니어
approver: Etch공정기술팀장
updatedAt: 2026-10-20
description: 한 줄 요약
tags: [Endpoint, OES]
---
```

| 필드 | 뜻 | 화면 | 근거 |
| --- | --- | --- | --- |
| `id` | 문서 번호. 접두어로 SOP/OCAP 구분 | ● | EPA G-6 §2.5, §3.1 |
| `title` | 제목 | ● | EPA G-6 §3.1 |
| `category` | 분류 | ● | |
| `version` | 개정 번호 (문자열) | ● | EPA G-6 §2.5 |
| `status` | `제정 중` / `시행` / `폐기` | | EPA G-6 §2.3 |
| `owner` | 주관 부서 | ● | EPA G-6 §3.1 |
| `author` | 작성자 | | EPA G-6 §3.1 Prepared by |
| `approver` | 승인자 | | EPA G-6 §3.1 Approved by |
| `updatedAt` | 최근 개정일 | ● | EPA G-6 §2.5 |
| `description` | 한 줄 요약 | ● | |
| `tags` | 검색 태그 | ● | |

언제·누가 작성했는지는 `author`·`approver`·`updatedAt`으로 보고, 지난 변경 내역은 본문 끝 **개정 이력** 표(버전, 날짜, 작성, 승인, 내용)로 봅니다. 연결 문서와 적용 장비는 메타데이터에 두지 않고 본문 §1과 §7에 씁니다.

## 본문 구조

**SOP** — EPA QA/G-6 §4.1(기술 SOP)·§4.2(관리 SOP) 항목을 TRACE에 맞게 줄인 순서입니다. 지침 스스로 "정답 형식은 없다"(§3)고 하므로, 기존 `SOP-ETCH-12#4.2` 조항 번호를 지키려고 절차를 §4에 둡니다.

`1 목적 및 적용 범위 · 2 용어 · 3 역할과 책임 · 4 절차 · 5 판정 기준·검증 · 6 기록 관리 · 7 참고 문서 · 8 개정 이력`

**OCAP** — Montgomery의 OCAP 3요소(Activator·Checkpoint·Terminator)와 반도체 OCAP 특허(US 12062558)의 "순서 있는 점검 항목 → 원인 분류 → 조치" 구조를 따릅니다. 각 Checkpoint는 `확인 / 이상 판정 / 원인 분류 / 조치` 네 줄로 씁니다.

`1 적용 범위 · 2 Activator · 3 즉시 조치 · 4 Checkpoints · 5 Terminator · 6 에스컬레이션 · 7 기록 항목 · 8 개정 이력`

OCAP ID는 특허 예시(`CMP-XXX`, `PH-CD`)처럼 `OCAP-{공정}-{항목}`으로 짓습니다.

## 조항 ID 규칙

- 번호로 시작하는 제목(`## 4.` / `### 4.2`)이 조항입니다. 조항 ID는 `{문서 id}#{번호}`입니다. 예: `SOP-ETCH-12#4.2`, `OCAP-ETCH-RF#4.3`
- 문서 MCP(`mcp/rag.py`)는 이 ID로 정확히 조회합니다. 개정할 때 기존 조항 번호를 바꾸지 않습니다. 없앨 조항은 번호를 비워 두고 개정 이력에 적습니다.
- `db/documents.json`에 있던 조항 문장은 새 조항의 첫 문장으로 그대로 옮겼습니다.

| 기존 조항 (documents.json) | 새 조항 |
| --- | --- |
| SOP-ETCH-12#4.2 | SOP-ETCH-12#4.2 (그대로) |
| WI-PM-07#3.1 | SOP-ETCH-01#4.6 |
| SPEC-RF-03#2.4 | OCAP-ETCH-RF#4.3 |
| WI-MFC-02#5.3 | OCAP-ETCH-PRS#4.3 |
| SPEC-EPD-01#6.2 | OCAP-ETCH-EPD#4.2 |

`db/documents.json`과 `db/cases.json`은 아직 기존 ID를 씁니다. seed를 이 폴더 기준으로 바꿀 때 위 표대로 ID를 옮깁니다.

## 작성 규칙

- 프론트엔드 마크다운 렌더러([markdown.js](../frontend/markdown.js))는 일부 문법만 지원합니다. **중첩 목록, HTML, mermaid를 쓰지 않습니다.** 표, 단일 단계 목록, 인용, 코드, 굵게는 됩니다.
- 문장은 짧은 단계형 능동문으로 씁니다 (EPA G-6 §1.4).
- 안전 경고는 해당 단계 바로 앞에 **경고:**로 씁니다 (EPA G-6 §4.1 d).
- 원인은 "확인 가설"로 쓰고 단정하지 않습니다.
- PHM 데이터는 표준화 값이라 물리 단위 없이 z-score로만 씁니다. 고장 기록 시각은 정지 시각입니다.

## 근거 자료

- [EPA QA/G-6 Guidance for Preparing Standard Operating Procedures (2001)](https://archive.epa.gov/region1/lab/web/pdf/g6-final.pdf): 표지 항목(§3.1), 문서 관리 표기(§2.5), 검토·승인(§2.2), 개정·정기 검토·폐기(§2.3, §2.6), 기술·관리 SOP 구성(§4.1, §4.2)
- [US 12062558 B2](https://patents.google.com/patent/US12062558): 반도체 OCAP. 공정 단계+항목으로 만든 OCAPID, 순서 있는 점검 항목과 원인 분류·실행 조치, MES hold/release 연동, 점검 결과 저장
- [Montgomery, Introduction to Statistical Quality Control, Ch.5 OCAP (강의 자료)](https://elearning.uniparthenope.it/mod/resource/view.php?id=23371): Activator·Checkpoint·Terminator. 원서 문구는 직접 확인하지 못했습니다.
- [ISO 9001:2015 §7.5.2 해설](https://www.thecoresolution.com/clause-7-5-2-iso-90012015-explained): 문서 식별(제목, 날짜, 작성자, 번호), 검토·승인. 표준 원문이 아닌 해설입니다.
- [INFICON — SEMI E10 장비 상태](https://www.inficon.com/en/news/what-do-we-mean-when-we-refer-to-tool-availability)
