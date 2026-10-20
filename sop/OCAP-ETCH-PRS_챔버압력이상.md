---
id: OCAP-ETCH-PRS
title: 챔버 압력 이상 대응
category: 설비 알람 대응
version: "1.0"
status: 시행
owner: Etch설비기술팀
author: Etch설비기술팀 엔지니어
approver: Etch설비기술팀장
updatedAt: 2026-10-20
description: 챔버 압력 또는 throttle valve 위치가 기준을 벗어났을 때 확인 순서와 조치입니다.
tags: [압력, Throttle valve, 진공, Leak, MFC]
---

> **샘플 문서**: 시연용 예시입니다. `[예시]` 수치는 확정 전에는 판정에 쓰지 않습니다.

## 1. 적용 범위

공정 단계: 식각. 감시 항목: 챔버 압력(mTorr), throttle valve 위치(%). 조사 공통 흐름은 SOP-ETCH-12를 따릅니다.

## 2. Activator

아래 중 하나가 나면 이 OCAP를 시작합니다.

- 압력 인터락 알람
- Step별 챔버 압력 평균이 기준 run 대비 |z| ≥ 3
- 압력은 정상이지만 throttle valve 위치가 기준 run 대비 |z| ≥ 3

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold합니다.
3. TRACE에 접수하고 SOP-ETCH-12 §4.3~4.4로 범위와 같은 조건 비교를 먼저 합니다.

## 4. Checkpoints

순서대로 확인하고, 이상이 확인된 항목에서 해당 조치를 합니다.

### 4.1 측정값 신뢰성

- 확인: 압력계 영점, 다른 압력계와의 차이
- 이상 판정: 두 압력계 차이가 `[예시]` 기준보다 큼
- 원인 분류: 압력 센서 이상
- 조치: 압력계 교정 또는 교체

### 4.2 운전 조건 일치

- 확인: recipe 버전, step 압력 설정값, 최근 recipe 변경
- 이상 판정: 기준 run과 설정이 다름
- 원인 분류: 운전 조건 불일치 (정상 공정 변화)
- 조치: 승인된 recipe로 복원, 이 경우 장비 고장으로 보지 않음

### 4.3 압력 변동과 etch rate 저하 동반

압력 변동과 etch rate 저하가 동반되면 MFC zero와 leak rate를 확인한다.

- 확인: MFC zero(OCAP-ETCH-GAS §4.2), 챔버 rate-of-rise leak rate(§4.5)
- 원인 분류: 가스 공급·제어 이상 또는 진공 누설
- 조치: OCAP-ETCH-GAS로 이동하거나 §4.5 수행

### 4.4 배기 계통

- 확인: throttle valve 위치와 응답 속도, 펌프 전류·회전 속도, foreline 압력
- 이상 판정: 같은 압력을 유지하려고 valve가 기준보다 더 열려 있음, 펌프 지표 이탈
- 원인 분류: 진공 배기 계통 이상
- 조치: valve 세정·교체, 펌프 점검

### 4.5 진공 누설

- 확인: 기저 압력까지 pump down 후 배기 밸브를 닫고 `[예시]` 5분간 압력 상승률 측정
- 이상 판정: 상승률이 `[예시]` 기준값 초과
- 원인 분류: 진공 누설
- 조치: He leak detector로 O-ring, 뷰포트, 피드스루 순으로 위치를 찾아 수리

## 5. Terminator

- 원인 조치 후 기저 압력, leak rate, step별 압력·valve 위치가 기준 run 분포 안 (|z| < 2)
- SOP-ETCH-01 §4.8 재인증 합격
- engineer 승인 후 Productive 복귀, hold lot은 SOP-ETCH-20으로 처분

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 발동 시각, 이상이 확인된 Checkpoint, 원인 분류, 조치, 조치 전후 값(단위 포함), 처리자, 승인자.

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch설비기술팀 | Etch설비기술팀장 | 제정 |
