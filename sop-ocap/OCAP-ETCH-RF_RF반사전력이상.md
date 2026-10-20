# OCAP-ETCH-RF RF 반사전력 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.1 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | RF Plasma Etch |
| 공정·감시 항목 | RF forward·reflected power, match tune·load 위치, RF·arc alarm |
| 필요 데이터 | recipe·step, RF 시계열, match preset·position, gas·pressure, calibration·PM·부품 이력 |
| 검증 가능 범위 | 현재 PHM 데이터로 직접 분석 불가. RF·match log와 제조사 승인 점검 필요 |

Reflected power 상승은 전달 전력과 plasma 안정성 변화의 관측 신호이며, 그 값만으로 match network 고장을 확정하지 않습니다.

## 2. Activator

- 경고: 안정 운전 구간의 reflected power 또는 match position이 승인된 주의 한계를 벗어남
- 이상: 승인된 관리 한계 이탈, match tuning 실패 또는 반복적인 안정 운전 편차
- 중대 이상: Arc·RF 전원 인터락 또는 match end-stop 알람

점화·step 전환 과도 구간은 안정 운전과 분리하되 고정된 제외 시간을 임의로 적용하지 않습니다. 펄스 RF는 같은 pulse 조건끼리 비교합니다. 아크는 OCAP-ETCH-ARC를 우선합니다.

## 3. 즉시 조치

1. 인터락, 아크 감지, match 끝단 도달이면 즉시 장비를 멈춥니다.
2. 장비 상태를 Unscheduled downtime으로 바꾸고 영향 lot을 SOP-ETCH-20에 따라 hold합니다.

## 4. Checkpoints

### 4.1 설정

#### 시나리오: 점화·Step 전환에만 Reflected Spike

- 관측: 점화 또는 power·gas step 전환 직후 spike가 있으나 안정 구간에서 회복함
- 데이터: forward/reflected 고해상도 시계열, match position, ignition·step event, gas·pressure
- 데이터 상태: PHM에는 RF·match·ignition 데이터가 없음
- 비교: 같은 chamber·recipe·step 전환과 pulse 조건의 대상 이전 run
- 우선 후보: 정상 과도 응답 또는 tuning 지연
- 지지 증거: 승인된 settling 구간 안에서 반복 가능하게 회복하고 interlock이 없음
- 반대 증거: Spike가 길어지거나 안정 구간까지 지속·증가함
- 판단 불가: 장비별 허용 settling 시간
- 다음 확인·이동: 제조사·recipe 승인 settling 기준을 조회하고 점화 실패이면 ARC로 이동
- 조사 결과: 정상 과도 / tuning 지연 / 미결로 기록

### 4.2 이력

#### 시나리오: 안정 구간 Reflected 상승과 Match Position 이동

- 관측: Forward command는 유사하지만 reflected가 높고 tune/load 위치가 기준에서 이동함
- 데이터: forward/reflected, tune/load, frequency, recipe·step, calibration·PM 이력
- 데이터 상태: 현장 RF log 필요
- 비교: 같은 chamber·recipe·step·pulse mode의 대상 이전 안정 run
- 우선 후보: Match tuning·전달 경로 변화 또는 plasma load 변화
- 지지 증거: 동일 공정 조건에서 match 위치가 점진적으로 끝단에 접근함
- 반대 증거: Gas·pressure·plasma emission이 먼저 변하고 match가 이를 따라감
- 판단 불가: Match 부품과 plasma load 중 1차 원인
- 다음 확인·이동: Gas·pressure가 동반되면 GAS·PRS, arc transient이면 ARC로 이동
- 조사 결과: Match 후보 / plasma load 후보 / 미결로 기록

### 4.3 반복 상승 시 접점과 calibration

Reflected power 상승이 반복될 경우 match network 접점과 calibration 상태를 확인한다.

#### 시나리오: 공정 조건은 동일한데 RF 계측·전달 지표가 장기 Drift

- 관측: 여러 이전 run에 걸쳐 reflected·match position 또는 insertion loss가 점진 이동함
- 데이터: RF calibration, forward/reflected metrology, match position, cable·접점·부품 PM, insertion loss
- 데이터 상태: PHM 미보유이며 RF 계측·정비 기록 필요
- 비교: 같은 chamber·recipe·step의 대상 이전 run만 사용하고 PM 전후를 분리
- 우선 후보: Calibration drift, connector·strap·match component 열화
- 지지 증거: Gas·pressure·OES는 안정하고 RF 경로 지표만 이동함
- 반대 증거: Plasma 조건이 함께 바뀌거나 기준 장비에서도 동일 변화가 있음
- 판단 불가: 물리 부품 상태
- 다음 확인·이동: 승인된 LOTO·제조사 점검을 요청하고 PM 직후이면 PM으로 이동
- 조사 결과: 계측 / 전달 경로 / match 내부 / 미결로 기록

### 4.4 Match 내부

- 가변 capacitor·motor의 물리 상태는 RF 데이터만으로 확정하지 않고 제조사 승인 점검 결과로만 확인합니다.

### 4.5 기준 장비 비교

#### 시나리오: Reflected 변화가 Gas·Pressure·OES 변화와 동반

- 관측: RF 편차와 plasma load를 바꾸는 gas·pressure·OES 변화가 같은 구간에 나타남
- 데이터: RF·match, gas·pressure, OES, recipe·step, chamber 상태
- 데이터 상태: PHM에는 해당 plasma 데이터 전체가 없음
- 비교: 같은 공정 조건의 대상 이전 run과 다른 chamber
- 우선 후보: Plasma impedance 변화; RF hardware는 2차 후보
- 지지 증거: 공정 신호 변화가 RF match 이동보다 먼저 발생함
- 반대 증거: 공정 신호는 안정하고 RF 경로 지표만 변함
- 판단 불가: 어떤 plasma chemistry 변화가 impedance를 바꿨는지
- 다음 확인·이동: 주 변화에 따라 GAS·PRS·OES로 이동하고 RF hardware 단정 금지
- 조사 결과: Plasma load / RF 경로 / 미결로 기록

### 4.6 공정 조건 교차 확인

- VSWR·reflected만으로 손실이나 부품 고장을 확정하지 않고 가능한 경우 insertion loss와 계측 위치를 함께 기록합니다.

## 5. Terminator

- 조사 종결: 설정·시점·전달 경로·공정 조건·PM 비교와 원인 후보가 기록됨
- 장비 복귀: RF·match 조건이 승인 기준 안이고 SOP-ETCH-01 §4.8 재인증을 통과함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 장비·chamber·recipe·step, run·lot ID, RF·match 값과 단위, 기준 run과 과도 구간 제외 기준, gas·pressure, 원인 후보별 근거와 미확인 사항, 연결 OCAP, calibration·insertion loss·VSWR, 조치, 조사 종결·복귀·lot 처분 승인.

## 8. 개정 이력

| 버전 | 날짜 | 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 초안 |
| 1.1 | 2026-10-20 | 적용 범위 메타데이터, ARC 연결, 원인 후보·교차 확인과 종결 결정 분리 | 현장 검토 전 |
