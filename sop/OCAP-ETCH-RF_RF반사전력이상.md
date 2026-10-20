---
id: OCAP-ETCH-RF
title: RF 반사전력 이상 대응
category: 설비 알람 대응
version: "1.0"
status: 시행
owner: Etch설비기술팀
author: Etch설비기술팀 엔지니어
approver: Etch설비기술팀장
updatedAt: 2026-10-20
description: RF reflected power가 상승했을 때 match network와 RF 전달 계통의 확인 순서와 조치입니다.
tags: [RF, 반사전력, Match network, Calibration]
---

> **샘플 문서**: 시연용 예시입니다. `[예시]` 수치는 확정 전에는 판정에 쓰지 않습니다.

## 1. 적용 범위

공정 단계: 식각. 감시 항목: RF forward·reflected power(W), match tune/load 위치. Reflected power가 커지면 플라즈마에 전달되는 전력이 줄어 etch rate·균일도가 바뀌고, generator가 과열되며, 플라즈마가 불안정해질 수 있습니다.

## 2. Activator

| 항목 | 주의 | 이상 |
| --- | --- | --- |
| reflected / forward | `[예시]` 2~5% | 5% 이상 또는 인터락 |
| reflected (기준 run 대비) | +20~50% | +50% 이상 |
| match 위치 | 한쪽 끝으로 치우침 | 끝단 도달 |

점화 직후와 step 전환 직후 `[예시]` 2초는 판정에서 뺍니다. 펄스 RF recipe는 같은 펄스 recipe 기준 run끼리만 비교합니다.

## 3. 즉시 조치

1. 인터락, 아크 감지, match 끝단 도달이면 즉시 장비를 멈춥니다.
2. 장비 상태를 Unscheduled downtime으로 바꾸고 영향 lot을 SOP-ETCH-20에 따라 hold합니다.

## 4. Checkpoints

### 4.1 설정

- 확인: recipe의 match preset, 튜닝 모드, 최근 recipe 변경
- 이상 판정: 표준값과 다름
- 원인 분류: 운전 조건 불일치
- 조치: 승인된 설정으로 복원

### 4.2 이력

- 확인: 마지막 RF calibration, 마지막 PM, reflected 상승 시작과 PM·부품 교체의 선후
- 이상 판정: 상승이 특정 작업 직후 시작
- 원인 분류: 작업 연관 의심 (단정 금지, SOP-ETCH-12 §4.6)
- 조치: 해당 작업 부위를 §4.3부터 우선 점검

### 4.3 반복 상승 시 접점과 calibration

Reflected power 상승이 반복될 경우 match network 접점과 calibration 상태를 확인한다.

- 반복: 같은 챔버·recipe step에서 주의 이상이 연속 3 run `[예시]` 또는 24시간 내 5 run `[예시]`
- 확인: SOP-ETCH-01 §4.1 LOTO 후 match 출력 접점, RF 스트랩, 케이블 커넥터의 변색·마모·토크, generator 출력·reflected 측정 calibration
- 원인 분류: 접점 열화 또는 calibration 이탈
- 조치: 접점 교체, 토크 재조정, RF calibration

### 4.4 Match 내부

- 확인: 가변 커패시터와 스텝 모터의 마모, 이동 범위
- 이상 판정: 이동 범위 축소, 마모
- 원인 분류: match 부품 열화
- 조치: 커패시터·모터 교체

### 4.5 기준 장비 비교

- 확인: 플라즈마 없이 전압·전류·위상을 측정해 정상 장비와 비교, insertion loss 측정
- 이상 판정: 정상 장비 대비 차이
- 원인 분류: RF 전달 경로 이상
- 조치: 경로 부품 교체. VSWR만으로 판단하지 않고 insertion loss를 함께 기록합니다. 임피던스가 커지면 reflected가 오히려 낮아 보일 수 있습니다.

## 5. Terminator

- 조치 후 reflected/forward 비와 match 위치가 기준 run 분포 안
- SOP-ETCH-01 §4.8 재인증 합격
- engineer 승인 후 Productive 복귀, hold lot은 SOP-ETCH-20으로 처분

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 이상 run ID와 step, reflected·forward 값(W)과 기준 대비 차이, 이상 Checkpoint, 원인 분류, 조치, calibration 전후 값, insertion loss·VSWR, 처리자, 승인자.

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch설비기술팀 | Etch설비기술팀장 | 제정 |
