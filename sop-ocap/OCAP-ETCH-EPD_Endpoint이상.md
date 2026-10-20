# OCAP-ETCH-EPD Endpoint 지연·미검출 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.1 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Endpoint 검출 기능이 있는 Plasma Etch 등 |
| 공정·감시 항목 | endpoint 검출 step, 검출 시간·성공 여부, 신호 세기·형상·잡음 |
| 필요 데이터 | endpoint 방식·원본 신호, recipe·step, threshold·gain·algorithm, RF·gas·pressure, window·광학계 PM, 잔막·과식각 계측 |
| 검증 가능 범위 | 현재 PHM 데이터로 직접 분석 불가. Endpoint·OES 원본과 추가 품질 계측 필요 |

Endpoint로 종료를 판정하는 recipe step에만 적용하고 시간 고정 step은 제외합니다.

## 2. Activator

- 경고: 같은 recipe·막종·endpoint 방식의 이전 run 대비 검출 시간·신호 형상이 승인된 주의 한계를 벗어남
- 이상: 승인된 관리 한계 이탈 또는 반복적인 검출 시간·신호 품질 이상
- 중대 이상: endpoint 미검출, timeout 강제 종료 또는 신호 상실

고정 비율은 사용하지 않으며 현장 승인 관리 한계와 제품 계측 기준을 적용합니다.

## 3. 즉시 조치

1. 경고는 원본 신호와 조건을 보존하고 다음 run 추세를 감시합니다.
2. 이상·중대 이상 wafer는 잔막·과식각 계측 대상으로 표시하고 SOP-ETCH-20에 따라 hold합니다.
3. 중대 이상이면 장비를 Unscheduled downtime으로 전환하고 후속 투입을 중지합니다.

## 4. Checkpoints

### 4.1 적용 조건·시간 비교와 실제 식각 지연 배제

#### 시나리오: Endpoint 지연과 실제 식각 조건 변화가 동반

- 관측: Endpoint 시간이 이동하고 RF·gas·pressure·temperature 또는 별도 etch rate도 함께 변함
- 데이터: endpoint raw signal·시간, recipe·막종·step, RF·gas·pressure·temperature, 전후 막 두께
- 데이터 상태: PHM에는 endpoint·etch rate·RF가 없어 분석 불가
- 비교: 동일 chamber·recipe 버전·막종·pattern exposure·endpoint 방식의 대상 이전 run
- 우선 후보: 실제 식각 진행 속도 변화
- 지지 증거: Raw signal 형상은 유지되지만 도달 시점이 이동하고 품질 계측도 같은 방향임
- 반대 증거: 공정·품질은 안정하고 optical intensity·SNR만 감소함
- 판단 불가: 별도 막 두께 계측이 없으면 실제 rate 변화 여부
- 다음 확인·이동: 주 동반 신호에 따라 RATE·RF·GAS·PRS·TMP로 이동
- 조사 결과: 실제 식각 지연 / 검출 문제 / 미결로 기록

### 4.2 Endpoint 신호와 검출 설정

Endpoint 신호 지연 시 window 오염, gain 설정, 광원 상태를 순차 점검한다.

#### 시나리오: 전체 Optical Signal이 점진적으로 약해짐

- 관측: 여러 파장 또는 endpoint channel의 절대 세기·SNR이 run에 따라 같이 감소함
- 데이터: Raw spectrum, exposure·gain, window cleaning·PM, RF·gas·pressure
- 데이터 상태: PHM 미보유; OES 원본과 광학계 이력 필요
- 비교: 같은 recipe·step의 마지막 승인 cleaning 이후 대상 이전 run
- 우선 후보: Window·optical path 오염 또는 detector 감도 변화
- 지지 증거: 공정 신호는 안정하고 여러 파장이 유사 비율로 감소함
- 반대 증거: 특정 species 파장만 바뀌거나 RF·gas·pressure도 변함
- 판단 불가: Window와 detector 중 원인 위치
- 다음 확인·이동: Spectrum 전체 분석은 OCAP-ETCH-OES §4로 이동
- 조사 결과: 광학 감쇠 / plasma 변화 / 미결로 기록

#### 시나리오: Threshold·Gain·Algorithm 변경 후 검출 시점 이동

- 관측: Raw signal은 이전 run과 유사하지만 판정 시점만 설정 변경과 함께 이동함
- 데이터: Raw signal, threshold·gain·filter·algorithm, recipe version, 변경 승인 이력
- 데이터 상태: 현장 endpoint 설정 이력 필요
- 비교: 동일 raw signal 조건에서 변경 전후 판정 결과
- 우선 후보: Endpoint 설정·recipe 불일치
- 지지 증거: 설정을 기준값으로 재현 계산했을 때 이전 판정 시점과 일치함
- 반대 증거: Raw signal 형상 자체가 달라짐
- 판단 불가: 변경의 제품 적정성
- 다음 확인·이동: 설정 승인 기록과 품질 계측을 요청
- 조사 결과: 설정 후보 / 신호 변화 / 미결로 기록

### 4.3 검출 계통과 PM 이력

#### 시나리오: 노출 면적·막종·Pattern 변화 후 Endpoint가 약해짐

- 관측: Recipe는 유사하지만 제품·막종·open area 변화 후 endpoint amplitude가 감소하거나 사라짐
- 데이터: 제품·막 stack, exposed area, pattern density, etch rate, OES wavelength·SNR
- 데이터 상태: PHM 미보유; 제품·layout·광학 데이터 필요
- 비교: 동일 막종·pattern exposure의 이전 run; blanket wafer와 제품 wafer를 혼합하지 않음
- 우선 후보: 검출 가능한 species 농도·노출 면적 부족 또는 막종 변경
- 지지 증거: 장비 공정 신호는 안정하고 제품군에 따라 재현됨
- 반대 증거: 같은 제품에서도 chamber별로만 발생하거나 모든 파장이 감소함
- 판단 불가: 최소 검출 면적과 신호 한계
- 다음 확인·이동: OES 검출 적합성 검토와 보완 계측을 지정
- 조사 결과: 제품 조건 / 광학계 / 공정 변화 / 미결로 기록

### 4.4 품질 영향과 후보 검증

- 잔막·과식각은 endpoint 시간만으로 확정하지 않고 막 두께·profile 계측으로 확인합니다.
- 실제 식각 변화, 광학계, 제품 노출 조건, 설정 후보를 나란히 비교하고 품질 계측 전에는 제품 영향을 확정하지 않습니다.

## 5. Terminator

- 조사 종결: 적용 조건·시간·신호·설정·광학계·품질 영향과 원인 후보가 기록됨
- 장비 복귀: endpoint 신뢰성과 관련 품질 지표가 승인 기준 안이고 SOP-ETCH-01 §4.8 재인증을 통과함
- Lot 처분: 잔막·과식각 계측 후 SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

모든 Checkpoint에서 이상을 찾지 못하면 SOP-ETCH-12 §4.9로 올립니다.

## 7. 기록 항목

공정 단계, OCAP ID, 장비·chamber·recipe·막종·step, run·lot ID, endpoint 방식·시간·지연률, 원본 신호·SNR, threshold·gain·algorithm, 기준 run, 원인 후보별 근거와 미확인 사항, 연결 OCAP, 품질 계측·조치, 조사 종결·복귀·lot 처분 승인.

## 8. 개정 이력

| 버전 | 날짜 | 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 초안 |
| 1.1 | 2026-10-20 | 5% 경고·10% 이상 기준 분리, 적용 범위 메타데이터, OES·품질 확인과 종결 결정 분리 | 현장 검토 전 |
