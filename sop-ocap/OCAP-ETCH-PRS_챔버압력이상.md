# OCAP-ETCH-PRS 챔버 압력 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.1 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Plasma Etch / Ion Mill 일부 |
| 공정·감시 항목 | 공정 step의 chamber pressure, pressure setpoint, throttle valve 위치·응답 |
| 필요 데이터 | 압력계·setpoint·valve 시계열, recipe·step, MFC·공급압, pump·foreline, leak check, PM 이력 |
| 검증 가능 범위 | 공정 압력과 Ion Mill pressure 일부 분석 가능. 센서·누설·배기 부품 확인은 추가 데이터 또는 현장 점검 필요 |

조사 공통 흐름은 SOP-ETCH-12를 따릅니다. 기저 압력·pump down·진공 누설이 중심이면 OCAP-ETCH-VAC를 적용합니다.

## 2. Activator

- 경고: 압력 또는 throttle valve가 승인된 관리 한계의 주의 영역에 있음
- 이상: 같은 recipe·step의 기준 run 대비 압력 또는 valve 위치가 |z| ≥ 3이거나 승인된 관리 한계를 벗어남
- 중대 이상: 압력 인터락, 목표 압력 유지 실패 또는 장비 보호 알람

## 3. 즉시 조치

1. 장비를 hold하고 상태를 Unscheduled downtime으로 바꿉니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold합니다.
3. TRACE에 접수하고 SOP-ETCH-12 §4.3~4.4로 범위와 같은 조건 비교를 먼저 합니다.

## 4. Checkpoints

순서대로 확인하고, 이상이 확인된 항목에서 해당 조치를 합니다.

### 4.1 측정값 신뢰성

#### 시나리오: 압력값만 이동하고 제어·공정 신호는 안정

- 관측: Pressure 값은 이동하지만 setpoint, throttle valve, gas readback, foreline은 이전 run과 유사함
- 데이터: 대상·이전 동일 recipe·step의 pressure, 보조 gauge, valve position, gas, foreline, gauge zero·교정 이력
- 데이터 상태: PHM은 IONGAUGEPRESSURE만 있어 gauge 간 비교·교정은 추가 데이터 필요
- 비교: 대상 시점 이전의 동일 Tool·recipe·step과 같은 gauge range
- 우선 후보: Pressure gauge zero·교정·range 문제
- 지지 증거: 보조 gauge와 불일치하거나 pump down·valve가 변하지 않음
- 반대 증거: 여러 gauge와 valve·pump 신호가 같은 방향으로 변함
- 판단 불가: Gauge 오염·열화의 물리 원인
- 다음 확인·이동: Gauge 점검 기록을 조회하고 실제 진공 성능도 변하면 OCAP-ETCH-VAC §4로 이동
- 조사 결과: 지지 / 약화 / 미결 / 데이터 부족으로 기록

### 4.2 운전 조건 일치

#### 시나리오: Setpoint 변경과 함께 압력이 이동

- 관측: Recipe·step의 pressure setpoint 또는 gas 설정 변경 시점과 압력 이동이 일치함
- 데이터: 승인 recipe 버전, setpoint, 실행 step, gas readback, 변경 승인 이력
- 데이터 상태: PHM recipe·recipe_step은 있으나 Plasma pressure setpoint와 변경 이력은 없음
- 비교: 같은 recipe 버전·step만 비교하고 버전이 다르면 별도 군으로 분리
- 우선 후보: 승인된 조건 변경 또는 잘못된 recipe 선택
- 지지 증거: 설정 변화량과 실제 압력 변화 방향이 일치함
- 반대 증거: 설정이 동일하거나 다른 chamber에는 같은 변화가 없음
- 판단 불가: 변경의 적정성과 제품 영향
- 다음 확인·이동: Recipe 승인 기록을 확인하고 gas 설정 문제이면 OCAP-ETCH-GAS §4로 이동
- 조사 결과: 정상 조건 변화 / 설정 불일치 / 미결로 기록

### 4.3 압력 변동과 etch rate 저하 동반

압력 변동과 etch rate 저하가 동반되면 MFC zero와 leak rate를 확인한다.

#### 시나리오: 압력과 Gas Readback이 함께 변함

- 관측: Pressure 편차와 특정 gas readback·공급압 편차가 같은 step에서 동반됨
- 데이터: setpoint·readback, 공급압, pressure, valve position, 동일 gas를 쓰는 다른 장비
- 데이터 상태: PHM은 Ar readback 일부만 있고 공급압·MFC setpoint는 없음
- 비교: 같은 Tool·recipe·step, 같은 gas channel의 대상 이전 run
- 우선 후보: Gas 공급·MFC 제어 변화
- 지지 증거: Gas 변화가 pressure 변화보다 먼저 시작하거나 다른 장비에도 공통 발생
- 반대 증거: Gas는 안정하고 valve·foreline만 변함
- 판단 불가: MFC zero drift, 실제 유량, valve leak-by
- 다음 확인·이동: 이동 사유를 기록하고 OCAP-ETCH-GAS §4를 수행
- 조사 결과: Gas 후보 지지 / 약화 / 데이터 부족으로 기록

### 4.4 배기 계통

#### 시나리오: 목표 압력을 유지하지만 Valve 보상량이 증가

- 관측: Pressure는 setpoint 부근이나 throttle valve position·응답이 기준에서 지속 이동함
- 데이터: pressure error, valve command·position, pump speed·current, foreline pressure, gas flow
- 데이터 상태: PHM에는 valve·foreline·pump 태그가 없어 현장 데이터 필요
- 비교: 같은 chamber·recipe·step과 유사 gas load의 대상 이전 run
- 우선 후보: Valve conductance 변화, 배기 성능 저하, chamber gas load 증가
- 지지 증거: Valve가 더 열린 상태에서도 pressure error가 증가하거나 foreline도 악화됨
- 반대 증거: Valve 변화가 recipe gas load 변경과 일치하고 pressure error가 없음
- 판단 불가: Valve 오염과 pump 성능 중 어느 쪽이 원인인지
- 다음 확인·이동: Pump down·base pressure도 악화되면 OCAP-ETCH-VAC §4로 이동
- 조사 결과: 배기 후보 지지 / 정상 보상 / 미결로 기록

### 4.5 진공 누설

#### 시나리오: Pressure·Base Pressure·Pump Down이 함께 악화

- 관측: 공정 pressure 불안정과 base pressure 상승 또는 pump down 지연이 동반됨
- 데이터: 전체 pump down curve, rate-of-rise, gauge, valve·pump·foreline, chamber 개방 이력
- 데이터 상태: PHM은 공정 중 ion gauge 일부만 있어 leak·outgassing 분리는 불가
- 비교: 같은 chamber 상태와 vent·PM 조건의 대상 이전 pump down
- 우선 후보: Leak, outgassing, pump·valve 성능 저하
- 지지 증거: 격리 후 pressure가 일정 기울기로 계속 상승하거나 leak detector 결과가 있음
- 반대 증거: 상승률이 시간에 따라 감소하고 최근 chamber 개방·세정이 있음
- 판단 불가: 누설 위치와 outgassing 성분
- 다음 확인·이동: 승인된 vacuum 진단을 위해 OCAP-ETCH-VAC §4로 이동
- 조사 결과: Leak 후보 / outgassing 후보 / pump 후보 / 미결로 기록

### 4.6 정비 이력과 후보 검증

- 최근 chamber cleaning, gauge·valve·pump PM과 설정 변경을 시나리오별 근거에 연결합니다.
- 정비 이후라는 선후관계만으로 원인을 확정하지 않고 OCAP-ETCH-PM §4의 정비 전후 비교로 검증합니다.

## 5. Terminator

- 조사 종결: 측정·recipe·gas·pressure control·vacuum·PM 비교와 원인 후보가 기록됨
- 장비 복귀: 원인 조치 후 관련 신호가 승인 기준 안이고 SOP-ETCH-01 §4.8 재인증을 통과함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 장비·chamber·recipe·step, run·lot ID, 발동 시각과 등급, 기준 run, 이상 Checkpoint, 원인 후보별 지지·반대 근거와 미확인 사항, 연결 OCAP와 이동 사유, 조치 전후 값(단위 포함), 조사 종결·장비 복귀·lot 처분 승인.

## 8. 개정 이력

| 버전 | 날짜 | 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 초안 |
| 1.1 | 2026-10-20 | 적용 범위 메타데이터, 경고·중대 이상, 원인 후보, VAC·PM 연결과 종결 결정 분리 | 현장 검토 전 |
