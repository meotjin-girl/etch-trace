# OCAP-ETCH-GRID Suppressor·이온 소스 그리드 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Ion Mill |
| 공정·감시 항목 | suppressor voltage·current, ion source·grid alarm, drift |
| 필요 데이터 | suppressor·beam 시계열, Ar flow, source usage, grid cleaning·교체·PM 이력, event log |
| 검증 가능 범위 | PHM 신호 일부 분석 가능. 오염·마모·단락은 제조사 승인 현장 점검 필요 |

## 2. Activator

- 경고: suppressor 신호의 지속 drift 또는 변동성 증가
- 이상: 설정값 대비 전압·전류 관리 한계 이탈 또는 관련 알람
- 중대 이상: source·grid 단락 또는 전원 인터락

## 3. 즉시 조치

1. 단락·전원 인터락이면 재가동하지 않고 승인된 정지·격리 절차를 따릅니다.
2. 영향 run·lot을 hold하고 event log와 원본 시계열을 보존합니다.
3. Source usage는 누적 카운터이므로 일반 센서 z-score 판정에서 제외합니다.

## 4. Checkpoints

### 4.1 Suppressor와 Beam 신호

1. Suppressor 전압의 설정·실제값을 확인합니다.
2. 전류의 평균·변동성·급변·반복 패턴을 확인합니다.
3. Beam voltage·current와 함께 움직였는지 비교합니다.

### 4.2 Gas·사용량·정비

Ar 공급, source usage의 누적 추세, grid cleaning·교체와 source 이벤트를 확인합니다.

### 4.3 현장 확인 필요 항목

그리드 오염·마모·단락 가능성은 제조사 승인 절차로 확인하도록 지정합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: grid 오염·마모, grid 간 단락 가능성, suppressor 전원·제어 문제, source 상태 변화
- 연결 OCAP: BEAM, GAS, PM, VAC
- 현장 확인 전에는 물리적 grid 고장을 확인된 원인으로 기록하지 않습니다.

## 5. Terminator

- 조사 종결: 관련 신호, 누적 사용량, 정비 이력과 원인 후보가 기록됨
- 장비 복귀: 제조사 승인 점검과 관련 신호 검증, SOP-ETCH-01 §4.8 재인증을 완료함
- Lot 처분: SOP-ETCH-20으로 별도 승인함

## 6. 에스컬레이션

단락·전원 인터락, grid 교체 기준 도달 또는 현장 점검 필요 시 설비 파트장과 장비 업체로 올립니다.

## 7. 기록 항목

장비·recipe·step, run·lot ID, suppressor·beam 신호와 단위, Ar flow, source usage 원값, event·PM·grid 이력, 기준 run, 원인 후보별 근거, 현장 확인 결과, 조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
