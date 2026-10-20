# OCAP-ETCH-GAS 가스 유량 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.1 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Plasma Etch / Ion Mill 일부 |
| 공정·감시 항목 | 공정 가스 MFC setpoint·readback, 공급 압력, valve 상태 |
| 필요 데이터 | gas 종류·MFC tag·F.S., recipe·step, 공급 압력, valve·MFC 교정·PM, chamber pressure, source·plasma 상태 |
| 검증 가능 범위 | Ion Mill Ar 유량 일부 분석 가능. 실제 유량·valve 누설은 교정 데이터 또는 현장 점검 필요 |

이온 밀의 Ar 유량(ETCHGASCHANNEL1READBACK, ETCHPBNGASREADBACK)을 포함합니다. 교정 기준은 장비 업체 매뉴얼과 사내 승인 표준을 따릅니다.

## 2. Activator

- 경고: readback·setpoint 차이 또는 기준 run 대비 변화가 승인된 주의 한계를 벗어남
- 이상: MFC 알람, 승인된 교정 허용차 초과 또는 같은 recipe·step 대비 |z| ≥ 3
- 중대 이상: 독성·가연성 가스 관련 인터락, 공급 상실 또는 안전 누출 의심

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold합니다.
3. 독성·가연성 가스 MFC를 분리해야 하면 SOP-ETCH-01 §4.1 LOTO와 퍼지를 먼저 합니다.

## 4. Checkpoints

### 4.1 Recipe와 적용 조건

#### 시나리오: Setpoint 변경 또는 잘못된 Recipe

- 관측: Gas readback 변화가 recipe·step·setpoint 변경과 같은 시점에 발생함
- 데이터: gas 종류, setpoint, readback, MFC F.S., recipe 버전·step, 변경 승인 이력
- 데이터 상태: PHM은 Ar readback과 recipe·step은 있으나 gas setpoint·F.S.는 없음
- 비교: 같은 Tool·recipe 버전·step과 MFC range
- 우선 후보: 승인된 조건 변화, recipe 선택 오류, MFC 운전 범위 부적합
- 지지 증거: Readback이 변경된 setpoint를 안정적으로 추종함
- 반대 증거: Setpoint가 동일하거나 readback이 추종하지 못함
- 판단 불가: 변경 조건의 공정 적정성
- 다음 확인·이동: 압력·beam도 변경 조건에 맞게 이동했는지 확인하고 필요 시 PRS·BEAM으로 이동
- 조사 결과: 정상 설정 변화 / 설정 오류 / 미결로 기록

### 4.2 공급 압력과 공통 계통

#### 시나리오: 여러 장비에서 같은 Gas가 동시에 변함

- 관측: 같은 gas utility를 쓰는 여러 장비에서 공급압·readback 이상이 겹침
- 데이터: 상류 공급압, gas cabinet·VMB event, 장비별 readback, valve 상태
- 데이터 상태: PHM에는 공통 utility와 다른 장비 동시 데이터가 없음
- 비교: 동일 시간대·동일 gas 공급 branch의 장비와 대상 이전 안정 구간
- 우선 후보: 공통 gas utility 또는 상류 regulator 문제
- 지지 증거: 장비·recipe가 달라도 같은 방향의 변화가 동시에 발생
- 반대 증거: 한 MFC·한 장비에만 국한됨
- 판단 불가: Utility의 물리 고장 위치
- 다음 확인·이동: Gas 설비 담당에게 공통 event를 요청하고 장비 내부 문제와 분리
- 조사 결과: 공통 utility 후보 / 장비 국부 후보 / 미결로 기록

### 4.3 MFC 상태와 zero

#### 시나리오: Zero 명령에서 비영점 Readback

- 관측: Zero setpoint에서 readback offset이 반복되며 저유량 step의 상대 편차가 큼
- 데이터: setpoint·readback, upstream/downstream shutoff, inlet pressure, orientation, warm-up·zero·교정 이력
- 데이터 상태: PHM에는 zero 조건·valve·inlet pressure가 없어 zero drift를 직접 판정할 수 없음
- 비교: 동일 설치·압력·온도·valve 조건의 승인된 zero check
- 우선 후보: MFC zero drift 또는 실제 valve leak
- 지지 증거: 양의 유량이 없도록 격리된 조건에서도 안정된 offset이 남음
- 반대 증거: 압력 상승이나 실제 flow가 있어 zero 조건이 성립하지 않음
- 판단 불가: Offset과 leak의 분리
- 다음 확인·이동: 제조사·사내 승인 zero/flow verification을 요청하고 임의 zero 조정은 금지
- 조사 결과: Zero drift 후보 / 실제 flow 후보 / 시험 조건 불충분으로 기록

### 4.4 유량 검증 (rate-of-rise)

#### 시나리오: Setpoint는 정상이나 Readback 추종이 느리거나 흔들림

- 관측: Step 시작 후 readback settling이 길거나 overshoot·oscillation이 반복됨
- 데이터: 고해상도 setpoint·readback·valve command, 공급압, pressure, step 경계, calibration 결과
- 데이터 상태: PHM readback은 있으나 setpoint·valve command가 없어 제어 편차 확정 불가
- 비교: 동일 MFC·gas·recipe·step의 대상 이전 transient와 안정 구간
- 우선 후보: MFC control valve 응답, 공급압 변동, sensor·controller 문제
- 지지 증거: 공급압은 안정하지만 readback 응답만 변함
- 반대 증거: 여러 gas channel과 chamber pressure가 함께 흔들림
- 판단 불가: 실제 유량 오차
- 다음 확인·이동: 승인된 rate-of-rise 또는 외부 flow verification 결과를 조회
- 조사 결과: 제어 응답 후보 / 공급압 후보 / 미결로 기록

### 4.5 밸브 상태와 leak-by

#### 시나리오: Zero Setpoint 이후 하류 Pressure가 계속 상승

- 관측: Gas command off 이후에도 downstream pressure 또는 chamber pressure가 증가함
- 데이터: setpoint·readback, upstream/downstream isolation, pressure trace, valve command·position
- 데이터 상태: PHM에는 isolation·valve feedback이 없어 현장 추가 확인 필요
- 비교: 같은 line의 정상 shutoff transient와 blank step
- 우선 후보: MFC valve leak-by, 외부 valve 누설, 다른 gas 유입
- 지지 증거: 격리 조합에 따라 pressure rise가 특정 valve 구간에 국한됨
- 반대 증거: 모든 gas가 차단되고 pressure rise가 outgassing 형태임
- 판단 불가: 누설 valve의 위치
- 다음 확인·이동: 승인된 leak test를 수행하고 chamber vacuum 문제이면 OCAP-ETCH-VAC §4로 이동
- 조사 결과: Valve 후보 / vacuum gas load 후보 / 미결로 기록

### 4.6 교차 신호와 정비 이력

- Chamber pressure, plasma·ion source, MFC 교체·교정, 공급 line 작업을 각 시나리오의 지지·반대 근거로 연결합니다.
- Pressure가 주 현상이면 PRS, beam과 Ar가 함께 변하면 BEAM, 정비 직후이면 PM으로 이동하고 이유를 기록합니다.

## 5. Terminator

- 조사 종결: recipe·공급·MFC·valve·교차 신호·정비 이력과 원인 후보가 기록됨
- 장비 복귀: 공급·유량이 승인 기준 안이고 SOP-ETCH-01 §4.8 재인증을 통과함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 장비·recipe·step, run·lot ID, 대상 MFC(가스·위치·일련번호·F.S.), setpoint·readback·공급 압력, valve 조건, zero·유량 검증, 기준 run, 원인 후보별 근거와 미확인 사항, 연결 OCAP, 조치, 조사 종결·복귀·lot 처분 승인.

## 8. 개정 이력

| 버전 | 날짜 | 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 초안 |
| 1.1 | 2026-10-20 | 적용 범위 메타데이터, 경고·중대 이상, 점검 순서와 종결 결정 분리 | 현장 검토 전 |
