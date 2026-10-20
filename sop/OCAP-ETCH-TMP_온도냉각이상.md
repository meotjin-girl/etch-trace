---
id: OCAP-ETCH-TMP
title: 온도·후면 냉각 이상 대응
category: 설비 알람 대응
version: "1.0"
status: 시행
owner: Etch설비기술팀
author: Etch설비기술팀 엔지니어
approver: Etch설비기술팀장
updatedAt: 2026-10-20
description: He 후면 냉각(이온 밀 FlowCool 포함) 압력·유량 또는 척 온도가 기준을 벗어났을 때 확인 순서와 조치입니다.
tags: [온도, He 후면 냉각, FlowCool, O-ring, PHM]
---

> **샘플 문서**: 시연용 예시입니다. PHM 2018 센서값은 표준화 값이므로 이 문서는 PHM 데이터에 물리 단위를 붙이지 않고 z-score로만 판정합니다.

## 1. 적용 범위

공정 단계: 식각. 감시 항목: He 후면 냉각 압력·유량, 척 온도, 이온 밀 FlowCool(FLOWCOOLPRESSURE, FLOWCOOLFLOWRATE)과 챔버 압력(IONGAUGEPRESSURE).

## 2. Activator

- He 후면 냉각 압력·유량 또는 척 온도 인터락
- Step별 냉각 압력·유량 평균이 기준 run 대비 |z| ≥ 3
- PHM 고장 기록: FlowCool Pressure Dropped Below Limit, Flowcool Pressure Too High Check Flowcool Pump, Flowcool leak

**주의:** PHM 고장 기록 시각은 운영자가 정비하려고 장비를 멈춘 시각입니다. 실제 이상은 그보다 먼저 시작됐을 수 있으므로 고장 시작 시각으로 쓰지 않습니다.

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 진행 중이던 웨이퍼는 냉각 상태를 알 수 없으므로 hold하고 계측 대상으로 표시합니다 (SOP-ETCH-20).
3. 소모품 카운터(ETCHSOURCEUSAGE 등)는 누적값이므로 편차 비교에서 뺍니다.

## 4. Checkpoints

### 4.1 측정값과 설정

- 확인: 냉각 압력 센서 상태, recipe의 He 압력·유량 설정값
- 이상 판정: 센서 판독 이상 또는 설정 변경
- 원인 분류: 센서 이상 또는 운전 조건 불일치
- 조치: 센서 교정, 승인된 설정으로 복원

### 4.2 유량·압력 패턴 판별

| 관찰 | 원인 분류 | 다음 확인 |
| --- | --- | --- |
| 유량 정상, 압력만 벗어남 | 냉각 회로 상태(센서, 펌프, 밸브) | 회로 압력 센서, 펌프 |
| 압력 이탈과 챔버 압력(IONGAUGEPRESSURE)이 함께 움직임 | 웨이퍼·고정구 O-ring 경계 누설 | §4.3, §4.4 |
| 압력 상한 초과 | 냉각 펌프·회로 막힘 | 펌프, 필터·배관 |
| 유량과 압력 모두 벗어남 | MFC 또는 He 공급 | OCAP-ETCH-GAS §4.1~4.2 |

### 4.3 웨이퍼·클램프 상태

- 확인: 해당 시점 웨이퍼 뒷면·가장자리 손상, 클램프·트레이 깨짐
- 이상 판정: 손상·깨짐 있음
- 원인 분류: 웨이퍼·클램프 기인 누설
- 조치: 클램프 교체, 웨이퍼 처분은 SOP-ETCH-20

### 4.4 O-ring과 척 오염

- 확인: SOP-ETCH-01 §4.1 LOTO 후 O-ring 손상·변형, 척 접촉면 퇴적물
- 이상 판정: 같은 압력에서 He 유량이 새 O-ring 장착 직후 기준값보다 `[예시]` 30% 넘게 높음
- 원인 분류: O-ring 열화 또는 척 오염
- 조치: O-ring 교체, 척 세정, 새 기준 유량 기록

### 4.5 냉각수(chiller)

- 확인: chiller 공급 온도·유량
- 이상 판정: 설정 대비 벗어남
- 원인 분류: 냉각수 계통 이상
- 조치: chiller 점검

## 5. Terminator

- 냉각 압력·유량이 설정값에서 안정
- Monitor wafer `[예시]` 2매에서 냉각 압력·유량·챔버 압력의 step별 z-score가 모두 |z| < 2
- engineer 승인 후 Productive 복귀, hold lot은 SOP-ETCH-20으로 처분

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 고장 기록명과 기록 시각(정지 시각임을 명시), 대상·기준 run ID, 센서별 step별 z-score와 평균 차이, 이상 Checkpoint, 원인 분류, 조치, O-ring 교체 여부와 새 기준 유량, 처리자, 승인자.

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch설비기술팀 | Etch설비기술팀장 | 제정 |
