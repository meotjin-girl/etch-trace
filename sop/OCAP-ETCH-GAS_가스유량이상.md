---
id: OCAP-ETCH-GAS
title: 가스 유량 이상 대응
category: 설비 알람 대응
version: "1.0"
status: 시행
owner: Etch설비기술팀
author: Etch설비기술팀 엔지니어
approver: Etch설비기술팀장
updatedAt: 2026-10-20
description: MFC 유량 readback이 설정값을 벗어났을 때 확인 순서와 조치입니다.
tags: [가스, MFC, Zero drift, Leak-by]
---

> **샘플 문서**: 시연용 예시입니다. MFC 교정 기준은 업체 매뉴얼과 사내 교정 표준을 따릅니다.

## 1. 적용 범위

공정 단계: 식각. 감시 항목: 공정 가스 MFC readback(sccm), 가스 공급 압력. 이온 밀의 Ar 유량(ETCHGASCHANNEL1READBACK, ETCHPBNGASREADBACK)도 포함합니다.

## 2. Activator

- MFC 유량 알람
- Readback이 설정값 대비 `[예시]` ±2% F.S. 초과
- Step별 유량 평균이 기준 run 대비 |z| ≥ 3

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold합니다.
3. 독성·가연성 가스 MFC를 분리해야 하면 SOP-ETCH-01 §4.1 LOTO와 퍼지를 먼저 합니다.

## 4. Checkpoints

### 4.1 공급 압력과 밸브 상태

- 확인: 가스 공급 압력, MFC 앞뒤 차단 밸브 상태, 같은 가스를 쓰는 다른 장비
- 이상 판정: 공급 압력 저하, 다른 장비도 같은 이상
- 원인 분류: 가스 공급 설비 이상 (장비 외부)
- 조치: 설비 담당에 통보, 장비 원인 조사 중단

### 4.2 MFC zero

- 확인: 유량 0 설정, 밸브 상태와 입구 압력을 매번 같은 조건으로 맞춘 뒤 `[예시]` 5분 안정화 후 판독
- 이상 판정: `[예시]` ±0.5% F.S. 초과
- 원인 분류: MFC zero drift
- 조치: zero 재조정 후 §4.3 재확인

### 4.3 유량 검증 (rate-of-rise)

- 확인: 알려진 부피의 배기를 닫고 설정 유량을 흘려 압력·온도 상승률로 실제 유량 계산
- 이상 판정: 실제 유량이 설정값 대비 `[예시]` ±1% 초과
- 원인 분류: MFC 교정 이탈
- 조치: MFC 교정, 불가하면 교체

### 4.4 밸브 leak-by

- 확인: 유량 0 설정에서 하류 압력 상승 여부
- 이상 판정: 유량 0인데 압력 상승
- 원인 분류: MFC 밸브 leak-by
- 조치: MFC 교체

### 4.5 설정 변경

- 확인: recipe의 유량 설정, MFC 범위(F.S.) 설정 변경 이력
- 이상 판정: 기준 run과 설정이 다름
- 원인 분류: 운전 조건 불일치
- 조치: 승인된 설정으로 복원

## 5. Terminator

- 교정·교체 후 zero와 유량 검증이 기준 안
- SOP-ETCH-01 §4.8 재인증 합격
- engineer 승인 후 Productive 복귀, hold lot은 SOP-ETCH-20으로 처분

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 대상 MFC(가스, 위치, 일련번호), 점검 시 밸브·입구 압력 조건, zero 판독값, 유량 검증값, 이상 Checkpoint, 원인 분류, 조치, 처리자, 승인자.

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch설비기술팀 | Etch설비기술팀장 | 제정 |
