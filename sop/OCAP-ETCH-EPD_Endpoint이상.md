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
description: OES endpoint가 늦거나 검출되지 않을 때 실제 식각 지연을 먼저 가려낸 뒤 검출 계통을 확인하는 순서입니다.
tags: [Endpoint, OES, Window, Gain]
---

> **샘플 문서**: 시연용 예시입니다. `[예시]` 수치는 확정 전에는 판정에 쓰지 않습니다.

## 1. 적용 범위

공정 단계: 식각. 감시 항목: endpoint 시간(sec), endpoint 신호 세기. Endpoint로 종료를 판정하는 recipe step에만 적용하고, 시간 고정 step은 제외합니다.

## 2. Activator

- Endpoint 시간이 기준 run 중앙값 대비 5% `[예시]` 이상 지연
- 최대 시간 도달(timeout)로 강제 종료

## 3. 즉시 조치

1. Timeout 웨이퍼는 잔막·과식각 계측 대상으로 hold합니다 (SOP-ETCH-20).
2. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.

## 4. Checkpoints

### 4.1 실제 식각 지연 배제

- 확인: SOP-ETCH-12 §4.2에 따라 RF, 압력, 가스 유량 이력을 함께 비교
- 이상 판정: 다른 계통도 함께 움직임
- 원인 분류: 실제 식각이 느려짐 (검출 계통 문제 아님)
- 조치: 해당 계통 OCAP로 이동. Endpoint 검출 계통 점검으로는 해결되지 않습니다.

### 4.2 Endpoint 신호 지연 시 순차 점검

Endpoint 신호 지연 시 window 오염, gain 설정, 광원 상태를 순차 점검한다.

1. Window 오염: 신호 절대 세기를 마지막 PM 직후 run과 비교합니다. 지연과 함께 세기가 꾸준히 줄었다면 창 안쪽 면의 폴리머·반응 부산물이 빛을 흡수·산란하고 있을 가능성이 큽니다.
2. Gain 설정: recipe의 gain·threshold가 표준값과 같은지, 최근 변경이 있는지 확인합니다.
3. 광원·검출기: 기준 광원으로 분광기와 광섬유 상태를 확인합니다.

- 원인 분류: window 오염 / 설정 불일치 / 검출기 이상
- 조치: window 세정·교체, 설정 복원, 검출기 수리

### 4.3 Window 세정·교체 후 확인

- 확인: SOP-ETCH-01 §4.6에 따라 세정 전후 신호 세기를 기록하고, seasoning 후 endpoint 시간과 신호 세기를 비교
- 이상 판정: 정상 범위로 돌아오지 않음
- 원인 분류: window 외 원인
- 조치: §4.2의 2·3번으로 돌아감

## 5. Terminator

- Endpoint 시간이 기준 run 중앙값 대비 5% `[예시]` 이내, timeout 없음
- 판정 시점 신호 변화 폭이 기준 run과 비슷함
- engineer 승인 후 Productive 복귀, hold lot은 SOP-ETCH-20으로 처분

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 이상 run ID, endpoint 시간(sec)과 기준 대비 지연률, 신호 세기, 이상 Checkpoint, 원인 분류, 조치, 설정 변경·window 세정 여부, 처리자, 승인자.

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch공정기술팀 | Etch공정기술팀장 | 제정 |
