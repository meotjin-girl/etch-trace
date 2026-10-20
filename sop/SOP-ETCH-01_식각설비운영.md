---
id: SOP-ETCH-01
title: 식각 설비 운영
category: 설비 운영
version: "1.0"
status: 시행
owner: Etch설비기술팀
author: Etch설비기술팀 엔지니어
approver: Etch설비기술팀장
updatedAt: 2026-10-20
description: 플라즈마 식각 설비의 정상 운전, 일상 점검, 예방정비, 생산 복귀 기준입니다.
tags: [식각, 운영, 예방정비, LOTO, 재인증]
---

> **샘플 문서**: 시연용 예시입니다. `[예시]` 수치는 장비 업체 매뉴얼과 공정 스펙으로 확정하기 전에는 판정에 쓰지 않습니다.

## 1. 목적 및 적용 범위

플라즈마 식각 설비를 정상 상태로 운전하고, 점검·정비 후 생산에 복귀시키는 기준을 정합니다. 이상이 감지되면 SOP-ETCH-12와 해당 OCAP를 따릅니다.

## 2. 용어

| 용어 | 뜻 |
| --- | --- |
| E10 장비 상태 | Productive, Standby, Engineering, Scheduled downtime, Unscheduled downtime, Non-scheduled (SEMI E10) |
| LOTO | 정비 전 에너지원을 차단하고 잠금·태그를 다는 절차 |
| Seasoning | 세정 후 dummy wafer로 챔버 벽 상태를 생산 수준으로 되돌리는 작업 |
| 재인증 | 정비·조치 후 monitor wafer로 생산 투입 가능 여부를 확인하는 작업 |
| 기준 run | 같은 장비·챔버·recipe의 정상 run. 선택 규칙은 SOP-ETCH-12 §4.4 |

## 3. 역할과 책임

| 역할 | 책임 | 자격 |
| --- | --- | --- |
| worker | 일상 점검, 장비 상태 전환, 정비 보조, 기록 | 설비 운전 교육, LOTO 교육 `[예시]` |
| engineer | 정비 계획, 판정, 재인증 합격 판정, 생산 복귀 승인 | 해당 설비 정비 교육 |
| admin | 문서·기준 관리, 조회 | — |

## 4. 절차

### 4.1 안전 경고와 에너지 차단

**경고:** 챔버를 열기 전 아래 에너지를 모두 차단하지 않으면 감전, RF 화상, 독성 가스 노출이 발생할 수 있습니다.

| 에너지 | 차단 후 잔류 에너지 처리 |
| --- | --- |
| 전기·히터 | 차단 후 무전압 확인 |
| RF generator·match | 출력 차단, 커패시터 방전 대기 |
| 공정 가스·He | 밸브 잠금, 퍼지, 잔압 해소 후 분리 |
| 진공 | N2 vent로 대기압 |
| 냉각수·고온 부품 | 유로 차단, 안전 온도 `[예시]` 40 °C 이하까지 냉각 |

1. 주변 작업자에게 정비 시작을 알립니다.
2. 정상 정지 절차로 장비를 멈춥니다.
3. 위 표의 차단 장치마다 개인 자물쇠와 태그(이름, 날짜, 사유)를 답니다.
4. 시동 시도와 측정기로 무전압·대기압을 확인합니다.
5. 작업 후 자물쇠는 단 사람이 직접 풀고, 에너지를 차례로 복구합니다.

### 4.2 장비 상태 전환

| 전환 | 실행 | 승인 |
| --- | --- | --- |
| 생산 → Unscheduled downtime | worker (알람·이상 감지 즉시) | 사후 engineer 확인 |
| 생산 → Scheduled downtime | worker | PM 계획 |
| downtime → Engineering (재인증) | worker | engineer |
| Engineering → Productive | worker | engineer (재인증 합격 후) |

상태 전환 시각은 조사의 기준 시각이 되므로 실제 전환 시점에 바로 입력합니다.

### 4.3 운전 시작 전 확인

1. 기저 압력과 최근 leak rate 결과가 기준 안에 있는지 확인합니다.
2. 공정 가스 공급 압력과 He 후면 냉각 압력·유량이 설정값에서 안정한지 확인합니다.
3. 투입할 recipe 버전이 승인된 버전인지 확인합니다.
4. FDC 감시 모델이 활성 상태인지 확인합니다.
5. 소모품 사용 카운터가 교체 기준 전인지 확인합니다.

### 4.4 정상 운전 감시

| 감시 항목 | 감시 방법 | 이탈 시 |
| --- | --- | --- |
| 챔버 압력, throttle valve 위치 | FDC step별 평균 | OCAP-ETCH-PRS |
| 가스 유량(MFC readback) | FDC setpoint 대비 | OCAP-ETCH-GAS |
| He 후면 냉각 압력·유량, 척 온도 | FDC, 인터락 | OCAP-ETCH-TMP |
| RF forward·reflected power | FDC step별 평균 | OCAP-ETCH-RF |
| Endpoint 시간 | SPC 관리도 | OCAP-ETCH-EPD |
| Etch rate, 균일도 | monitor wafer SPC | SOP-ETCH-12 |

### 4.5 예방정비 주기

| 항목 | 주기 `[예시]` | 근거 |
| --- | --- | --- |
| 챔버 wet clean·seasoning | RF 누적 시간 또는 3,000매 중 먼저 도달 | 업체 PM 매뉴얼 |
| Endpoint window 세정 | wet clean과 동시 | SPC 신호 세기 추이 |
| 고정구 O-ring | 6개월 또는 He 유량 기준 초과 | OCAP-ETCH-TMP §4.4 |
| RF calibration | 6개월 | 업체 매뉴얼 |
| MFC zero 점검 | 3개월 | 사내 교정 표준 |

### 4.6 세정 전후 값 보존

폴리머 누적 또는 endpoint window 오염이 의심되면 세정 전후 값을 보존하고 seasoning 결과를 기록한다.

- 세정 전: 마지막 정상 run 3건의 etch rate, endpoint 시간, RF reflected power, 챔버 압력, endpoint 신호 세기
- 세정 후: seasoning 각 웨이퍼의 같은 항목과 재인증 결과
- 이 값이 없으면 PM 효과를 다음 조사에서 판단할 수 없으므로 PM을 완료 처리하지 않습니다.

### 4.7 Wet clean과 seasoning

1. §4.1에 따라 에너지를 차단하고 챔버를 N2로 vent합니다.
2. 상부 전극, 라이너, focus ring, endpoint window를 분리하고 오염 상태를 사진으로 남깁니다.
3. 부품별 지정 방법으로 세정하고, O-ring과 기준 미달 소모품을 교체합니다. 교체 부품의 품번·lot을 기록합니다.
4. 지정 토크로 조립하고 기저 압력까지 pump down 합니다.
5. Rate-of-rise leak check가 기준을 넘으면 4단계부터 다시 합니다.
6. Dry clean 후 dummy wafer로 seasoning을 합니다 (`[예시]` 25매).
7. 마지막 3매의 etch rate가 PM 전 기준 중앙값 ±3% `[예시]` 안이면 종료합니다. 두 번 반복해도 안정되지 않으면 SOP-ETCH-12 §4.9로 올립니다.

### 4.8 재인증과 생산 복귀

1. Monitor wafer `[예시]` 3매로 etch rate, 균일도, 파티클을 측정합니다.
2. 모든 값이 기준 run 분포 안 (`[예시]` 중앙값 ±3%)이면 engineer가 복귀를 승인합니다.
3. worker가 장비 상태를 Productive로 바꿉니다.
4. 재인증 2회 연속 실패 시 SOP-ETCH-12 §4.9로 올립니다.

## 5. 판정 기준·검증

- Seasoning run과 재인증 run은 이후 조사의 기준 run으로 쓰지 않습니다.
- 재인증 합격 판정은 작업자가 아닌 engineer가 합니다.

## 6. 기록 관리

장비 이력(e-logbook)에 아래를 남깁니다: 작업 구분(PM/비정기), 시작·종료 시각, 작업자, 차단한 에너지원과 자물쇠 부착자, §4.6의 세정 전후 값, 교체 부품 품번·lot, leak check·seasoning·재인증 결과, 복귀 승인자, 연결된 TRACE 조사 ID.

## 7. 참고 문서

- SOP-ETCH-12 식각 장비 이상 대응
- SOP-ETCH-20 Lot Hold/Release
- OCAP-ETCH-PRS, OCAP-ETCH-GAS, OCAP-ETCH-TMP, OCAP-ETCH-RF, OCAP-ETCH-EPD

## 8. 개정 이력

| 버전 | 날짜 | 작성 | 승인 | 내용 |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-10-20 | Etch설비기술팀 | Etch설비기술팀장 | 제정 |
