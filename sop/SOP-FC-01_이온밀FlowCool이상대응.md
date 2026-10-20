# SOP-FC-01 이온 밀 FlowCool 이상 대응

| 항목 | 내용 |
|---|---|
| 문서 ID | SOP-FC-01 |
| 개정 | Rev 0.1 (예시, 2026-10-20) |
| 적용 장비 | 이온 밀(IBE) 식각 장비의 FlowCool(He/물 웨이퍼 후면 냉각) 계통 |
| 데이터 | PHM 2018 Data Challenge 센서 (표준화 값, 단위 없음) |
| 관련 문서 | SOP-ETCH-12, SOP-SAFE-01 |

> `[예시]` 수치는 시연용이다. PHM 센서값은 표준화된 값이므로 이 문서는 물리 단위를 쓰지 않고 z-score로만 판정한다.

## 1. 목적

FlowCool 알람이 났을 때, 냉각 회로 문제인지 웨이퍼·O-ring 경계 누설인지 데이터로 좁힌 뒤 정비하게 한다.

## 2. 대상 고장

| 고장 기록명 | 의미 |
|---|---|
| FlowCool Pressure Dropped Below Limit | FlowCool 회로 He 압력이 하한 아래로 떨어짐 |
| Flowcool Pressure Too High Check Flowcool Pump | He 압력이 상한을 넘음, 펌프 확인 필요 |
| Flowcool leak | FlowCool과 진공 챔버 사이 누설 |

**주의:** 고장 기록 시각은 운영자가 정비하려고 장비를 멈춘 시각이다. 실제 이상은 그보다 훨씬 먼저 시작됐을 수 있고, 그 시작 시각은 기록에 없다. 고장 기록 시각을 고장 시작으로 쓰지 않는다.

## 3. 즉시 조치

SOP-ETCH-12 §4.1과 같다. 진행 중 웨이퍼는 냉각 상태를 확인할 수 없으므로 hold하고 별도 계측 대상으로 표시한다.

## 4. 데이터 확인 순서

### 4.1 비교 단위와 기준

- 조사 단위는 run_id(`{runnum}-{Lot}`)다. 한 run_id 안에서 recipe는 하나다.
- 기준 run은 같은 장비·같은 recipe의 이전 run이다. 고장 기록 직전 24시간 안에 끝난 run은 뺀다. 3건 미만이면 비교하지 않고 범위 확대를 묻는다.
- recipe_step별 센서 평균으로 z-score를 낸다. |z| ≥ 3은 확인 필요 편차, 2 ≤ |z| < 3은 경미한 편차로 쓴다. 기준 표준편차가 0에 가까우면 평균 차이(target_mean − ref_mean)를 함께 적는다.
- 소모품 카운터(ETCHSOURCEUSAGE, ETCHAUXSOURCETIMER, ETCHAUX2SOURCETIMER)는 누적값이라 편차 비교 대상이 아니다.

### 4.2 먼저 볼 센서

FLOWCOOLPRESSURE, FLOWCOOLFLOWRATE를 먼저 보고, 그다음 IONGAUGEPRESSURE를 본다.

### 4.3 판단 분기 (확인 가설)

| 관찰 | 확인 가설 | 다음 확인 |
|---|---|---|
| 유량 정상, 압력만 벗어남 | FlowCool 회로 상태 (압력 센서, 펌프, 밸브) | 회로 압력 센서 calibration, 펌프 상태 |
| 압력 벗어남 + 챔버 압력(IONGAUGEPRESSURE)도 함께 움직임 | 웨이퍼·고정구 O-ring 경계 누설 | O-ring, 웨이퍼 뒷면·가장자리, 고정구 오염 |
| 압력 상한 초과 | FlowCool 펌프·회로 막힘 | 펌프, 회로 필터·배관 |
| 유량과 압력 모두 벗어남 | MFC 또는 He 공급 | He 공급 압력, FlowCool MFC (WI-MFC-02 §5.1 준용) |

이 표는 조사 가설이며 원인 확정이 아니다. 보고서에는 근거 run_id와 z-score를 함께 적는다.

## 5. 정비

1. SOP-SAFE-01 §3 LOTO 후 진행한다. He 라인은 닫고 잔압을 뺀 뒤 분리한다.
2. 고정구 O-ring 상태를 확인하고 손상·변형이 있으면 교체한다.
3. 고정구 접촉면의 오염(퇴적물, 이물)을 세정한다.
4. 누설 가설이면 해당 시점 웨이퍼의 뒷면·가장자리 손상 여부를 확인한다.
5. 새 O-ring 장착 직후, 정해진 압력에서의 He 유량을 **기준값**으로 기록한다. 이후 같은 압력에서 유량이 기준값보다 `[예시]` 30% 넘게 오르면 O-ring 교체·세정 시점으로 본다.

## 6. 복귀

1. 펌프 다운 후 FlowCool 압력·유량이 설정값에서 안정되는지 확인한다.
2. monitor wafer `[예시]` 2매를 처리하고, FLOWCOOLPRESSURE·FLOWCOOLFLOWRATE·IONGAUGEPRESSURE의 step별 z-score가 모두 |z| < 2인지 확인한다.
3. engineer 승인 후 Productive로 바꾼다.

## 7. 기록

- 고장 기록명, 고장 기록 시각(정지 시각임을 명시), 대상·기준 run_id 목록
- 센서별 step별 z-score와 평균 차이 (단위 없음)
- 정비 내용, O-ring 교체 여부와 새 기준 유량
- 복귀 확인 결과

## 8. 개정 이력

| Rev | 날짜 | 내용 |
|---|---|---|
| 0.1 | 2026-10-20 | 예시 초안. `backend/knowledge/investigation_guide.md`의 FlowCool 확인 순서를 SOP로 옮김 |
