# OCAP-ETCH-TMP 온도·후면 냉각 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.1 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | He 냉각을 사용하는 Plasma Etch / Ion Mill |
| 공정·감시 항목 | He 후면 냉각 pressure·flow, chuck temperature, FlowCool, chamber pressure |
| 필요 데이터 | 냉각 설정·sensor 시계열, recipe·step, chamber pressure, He·chiller·valve, wafer·clamp·O-ring, PM 이력 |
| 검증 가능 범위 | PHM FlowCool은 직접 추세 분석 가능. 밀봉·고정구·chiller 원인 확정에는 추가 데이터 또는 현장 점검 필요 |

FlowCool 태그는 FLOWCOOLPRESSURE, FLOWCOOLFLOWRATE이고 관련 chamber pressure는 IONGAUGEPRESSURE입니다. 표준화 값은 물리 단위 없이 z-score로만 판정합니다.

## 2. Activator

- 경고: 냉각 pressure·flow 또는 chuck temperature가 승인된 주의 한계를 벗어나거나 drift함
- 이상: 같은 recipe·step 대비 |z| ≥ 3 또는 FlowCool 계통 고장 이벤트
- 중대 이상: 냉각·온도 인터락, 냉각 상실 또는 wafer 온도 안전 범위 이탈

**주의:** FlowCool 고장 기록 시각은 운영자가 정비하려고 장비를 멈춘 시각입니다. 실제 이상은 그보다 먼저 시작됐을 수 있으므로 고장 시작 시각으로 쓰지 않습니다.

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 진행 중이던 웨이퍼는 냉각 상태를 알 수 없으므로 hold하고 계측 대상으로 표시합니다 (SOP-ETCH-20).
3. 소모품 카운터(ETCHSOURCEUSAGE 등)는 누적값이므로 편차 비교에서 뺍니다.

## 4. Checkpoints

### 4.1 측정값과 설정

#### 시나리오: FlowCool Pressure Dropped Below Limit

- 관측: FLOWCOOLPRESSURE가 같은 step의 이전 분포보다 낮거나 관련 고장 기록이 있음
- 데이터: FLOWCOOLPRESSURE, FLOWCOOLFLOWRATE, IONGAUGEPRESSURE, recipe·step, wafer·fixture 상태
- 데이터 상태: PHM에서 세 신호를 직접 비교할 수 있으나 익명값이라 물리 단위를 붙이지 않음
- 비교: 대상 이전 동일 Tool·recipe·step; 고장 정지 직전 run을 확정 정상으로 쓰지 않음
- 우선 후보: He 공급 저하, control 문제, seal·wafer 경계 누설, pressure sensor 문제
- 지지 증거: Flow도 함께 감소하면 공급·제어 후보, chamber pressure가 함께 움직이면 경계 누설 후보
- 반대 증거: Pressure만 단독 이동하고 반복·교차 신호가 없음
- 판단 불가: O-ring·wafer·pump의 물리 상태
- 다음 확인·이동: Ar가 아니라 He 공급 제어 데이터와 fixture 현장 점검을 요청하고 gas 공통 이상이면 GAS로 이동
- 조사 결과: 공급 / 누설 / sensor / 미결로 기록

### 4.2 유량·압력 패턴 판별

#### 시나리오: FlowCool Pressure Too High Check FlowCool Pump

- 관측: FLOWCOOLPRESSURE가 상승하고 PHM의 Too High 고장 기록 또는 pump 관련 event가 있음
- 데이터: Pressure·flow 시계열, step·recipe, pump·valve·filter 상태, water cooling·temperature
- 데이터 상태: PHM에는 FlowCool pressure·flow만 있고 pump·water sensor는 없음
- 비교: 대상 이전 동일 조건의 안정 구간과 step 전환 transient
- 우선 후보: Pump·valve control, restriction·blockage, pressure sensor 이상
- 지지 증거: Flow 감소와 pressure 상승이 동반되거나 pump event가 선행함
- 반대 증거: Flow와 pressure가 함께 정상적으로 setpoint 변경을 추종함
- 판단 불가: Pump, filter, line 중 물리 위치
- 다음 확인·이동: Pump·valve·water loop 데이터를 요청하고 임의 분해 없이 승인된 현장 점검으로 연결
- 조사 결과: 제어 / restriction / sensor / 미결로 기록

### 4.3 시간적 변화와 관련 신호

#### 시나리오: FlowCool Leak

- 관측: FlowCool pressure·flow 관계가 이전 run과 달라지고 IONGAUGEPRESSURE가 동반 변화함
- 데이터: 세 센서의 step별 시계열, wafer·fixture·O-ring 이력, 고장 정지 시각
- 데이터 상태: PHM 직접 비교 가능하지만 고장 기록 시각은 물리적 누설 시작 시각이 아님
- 비교: 대상 시점 이전 동일 Tool·recipe·step을 역추적하고 미래 fault·TTF는 사용하지 않음
- 우선 후보: Wafer·fixture O-ring 경계 누설
- 지지 증거: FlowCool 변화와 chamber pressure 변화가 반복적으로 시간 정렬됨
- 반대 증거: Chamber pressure는 안정하거나 다른 gas·vacuum 변화가 더 먼저 발생함
- 판단 불가: 누설 위치·크기와 wafer 손상 여부
- 다음 확인·이동: 승인된 seal·wafer 점검을 요청하고 base vacuum도 악화되면 VAC로 이동
- 조사 결과: 경계 누설 후보 / vacuum 후보 / 미결로 기록

### 4.4 웨이퍼·클램프 상태

- Wafer backside·edge, clamp·fixture 검사 결과는 센서 가설을 확인하는 별도 현장 증거로 기록합니다.
- 검사 전에는 wafer·clamp 손상을 확정 원인으로 쓰지 않으며 제품 처분은 SOP-ETCH-20으로 분리합니다.

### 4.5 O-ring과 척 오염

- O-ring·접촉면 상태는 제조사·사내 승인 절차로 확인하며 문서에 임의의 유량 임계치를 두지 않습니다.
- 점검 전후 같은 recipe·step의 pressure·flow 관계와 chamber pressure를 보존합니다.

### 4.6 냉각수·공급·정비 이력

- Chiller·water loop, He 공급·valve, 관련 PM·부품 교체는 PHM 미보유 데이터로 명시합니다.
- 현장 데이터가 확보되면 Low·Too High·Leak 각 시나리오의 후보를 지지하거나 약화하는 근거로 연결합니다.

## 5. Terminator

- 조사 종결: sensor·설정·시간 변화·관련 신호·밀봉·chiller·PM 비교와 원인 후보가 기록됨
- 장비 복귀: 냉각 계통이 승인 기준 안이고 SOP-ETCH-01 §4.8 재인증을 통과함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 장비·recipe·step, run·lot ID, 고장 기록명과 정지 시각, 대상·기준 run, sensor별 z-score와 평균 차이, 원인 후보별 지지·반대 근거와 미확인 사항, 연결 OCAP, 현장 점검·조치, 조사 종결·복귀·lot 처분 승인.

## 8. 개정 이력

| 버전 | 날짜 | 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 초안 |
| 1.1 | 2026-10-20 | 적용 범위 메타데이터, 시간적 변화, 원인 후보와 재인증 기준 통일 | 현장 검토 전 |
