# OCAP-ETCH-CD CD·식각 프로파일 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | 계측 가능한 Plasma Etch / Ion Mill 패턴 공정 |
| 공정·감시 항목 | CD bias, 식각 깊이, 측벽 각도, bowing, taper, notching, microtrenching, residue |
| 필요 데이터 | CD-SEM·profile 원본, 측정 위치·recipe, lithography CD, 막·mask, 식각 recipe·step, 장비·PM 이력 |
| 검증 가능 범위 | 품질 패턴과 공정 조건 연관성 분석 가능. CD-SEM 등 추가 계측 필요 |

> PHM 2018에는 CD·profile·lithography 계측값이 없습니다. 기술 근거: SRC-THERMO-CD, SRC-PROFILE-ETCH, SRC-PHM-2018.

## 2. Activator

- 경고: CD·profile 지표가 관리 한계의 주의 영역에 있거나 지속적으로 변함
- 이상: CD bias, 측벽 각도, 식각 깊이, profile 또는 residue가 승인된 규격을 벗어남
- 중대 이상: 다수 wafer 또는 핵심 제품에서 기능·수율 영향이 예상됨

## 3. 즉시 조치

1. 계측 이미지와 원본 값, 측정 위치를 보존합니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold하고 같은 조건의 후속 투입 여부를 engineer가 결정합니다.

## 4. Checkpoints

### 4.1 불량 형태와 계측

#### 시나리오: Global CD Bias

- 관측: wafer 전반의 post-etch CD가 lithography CD 대비 같은 방향으로 이동하는지 봅니다.
- 필요 데이터·존재 여부: pre/post CD, 좌표·계측 recipe·이미지가 필요하며 PHM에는 없습니다.
- 비교 Run: 동일 제품·mask·막·recipe·계측 조건의 대상 이전 run을 비교합니다.
- 패턴→후보: pre-CD부터 이동하면 lithography, post에서만 이동하면 etch 조건·시간을 우선합니다.
- 지지 근거: 반복 계측과 pre/post bias의 일관성, 관련 공정 신호 변화입니다.
- 반대 근거: 재측정 불일치 또는 pre-CD만으로 결과가 설명됩니다.
- 판단 불가: pre-CD가 없으면 lithography와 etch 기여를 분리할 수 없습니다.
- 추가 확인: CD-SEM 원본, over-etch·gas·pressure·RF/beam을 확인합니다.
- 이동 조건·조사 결과: 식각 속도·시간 동반이면 RATE/STEP/EPD로 이동해 후보별 판정을 기록합니다.

#### 시나리오: Bowing·Taper

- 관측: 단면의 측벽 각도와 깊이별 CD 변화를 봅니다.
- 필요 데이터·존재 여부: 동일 위치 단면 이미지, mask·막 구조, recipe step이 필요합니다.
- 비교 Run: 같은 구조·방향·단면 조건의 대상 이전 run을 비교합니다.
- 패턴→후보: 전체 wafer 공통이면 chemistry·압력·에너지, 위치 의존이면 균일도·열상태를 우선합니다.
- 지지 근거: 다수 단면 재현과 관련 step 신호 변화입니다.
- 반대 근거: 단면 준비 artifact 또는 mask profile로 설명됩니다.
- 판단 불가: 단일 2D 단면으로 wafer 전체 profile을 일반화할 수 없습니다.
- 추가 확인: 복수 위치 단면, GAS·PRS·RF/BEAM·TMP 데이터를 조회합니다.
- 이동 조건·조사 결과: 공간 패턴이면 UNI, 공정 신호면 해당 OCAP으로 이동하고 근거를 남깁니다.

### 4.2 식각 전 상태와 공정 조건

#### 시나리오: Notching·Microtrenching

- 관측: feature 하단·edge의 국부 과식각 형태와 패턴 의존성을 봅니다.
- 필요 데이터·존재 여부: 단면 이미지, feature 구조·막종, step별 recipe와 over-etch 정보가 필요합니다.
- 비교 Run: 동일 구조·막·mask·recipe의 대상 이전 run을 비교합니다.
- 패턴→후보: 특정 interface/feature에서 재현되면 charge·ion angle·over-etch 가설을 우선 검토합니다.
- 지지 근거: 구조 의존 재현, bias/beam·압력·시간 변화와 일치입니다.
- 반대 근거: lithography·단면 artifact이거나 장비 조건 변화 없이 구조만 다릅니다.
- 판단 불가: profile만으로 미시적 메커니즘이나 특정 부품 고장을 확정할 수 없습니다.
- 추가 확인: 공정 통합 검토와 step별 RF/BEAM·PRS·시간 데이터를 확인합니다.
- 이동 조건·조사 결과: 에너지 관련이면 RF/BEAM, 종료시간이면 STEP/EPD로 이동해 판단 한계를 기록합니다.

### 4.3 온도·Chamber·공통성

#### 시나리오: Lithography 영향과 Etch 영향 분리

- 관측: 동일 wafer 좌표에서 pre-CD·mask profile과 post-etch profile의 변화를 연결합니다.
- 필요 데이터·존재 여부: pre/post 계측과 wafer genealogy가 필요하며 없으면 분리 판단이 불가합니다.
- 비교 Run: 동일 lithography 조건이 다른 etch chamber를 통과한 run과 역비교합니다.
- 패턴→후보: lithography lot에 묶이면 incoming, etch chamber에 묶이면 chamber·recipe를 우선합니다.
- 지지 근거: 교차 분류에서 한 축에 재현되고 독립 계측이 일치합니다.
- 반대 근거: 제품·계측기 confound를 통제하면 차이가 사라집니다.
- 판단 불가: genealogy 또는 matched-run이 없으면 인과 분리가 불가능합니다.
- 추가 확인: 공정통합·계측 담당과 교차표를 만들고 chamber·PM 이력을 확인합니다.
- 이동 조건·조사 결과: chamber 특이성이면 PM/UNI, incoming이면 관련 전공정으로 이관하고 결과를 기록합니다.

### 4.4 원인 후보와 추가 검증

계측과 식각 전 상태를 확인하기 전에는 장비 원인으로 확정하지 않습니다. 조사 결과에는 profile 유형, 지지·반대 증거, 미확인 사항과 다음 조회를 남깁니다.

## 5. Terminator

- 조사 종결: 불량 형태, 식각 전후 조건, 영향 범위와 원인 후보가 기록됨
- 장비 복귀: CD·profile 관련 품질 기준과 SOP-ETCH-01 §4.8 재인증을 만족함
- Lot 처분: 영향을 받은 wafer를 SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

기능·수율 영향이 예상되거나 lithography와 etch 영향을 구분할 수 없으면 공정통합·계측·품질 담당에게 올립니다.

## 7. 기록 항목

장비·chamber·recipe·step, run·lot·wafer ID, 제품·막·mask, CD·profile 값과 단위, 이미지·좌표·계측 recipe, lithography 기준, 기준 run, 원인 후보별 근거, 연결 OCAP, 조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
