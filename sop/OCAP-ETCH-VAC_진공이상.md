# OCAP-ETCH-VAC 진공 배기·기저 압력·누설 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Plasma Etch / Ion Mill |
| 공정·감시 항목 | base pressure, pump down 시간·곡선, 진공 유지, leak, pump·foreline |
| 필요 데이터 | 압력 gauge, pump down trace, pump·valve·foreline, gas 차단 상태, leak check, chamber 개방·PM 이력 |
| 검증 가능 범위 | Ion gauge pressure 일부 분석 가능. 누설 위치와 부품 상태는 승인된 현장 점검 필요 |

## 2. Activator

- 경고: pump down 시간이 증가하거나 base pressure가 주의 한계를 벗어남
- 이상: base pressure·배기 성능 관리 한계 이탈 또는 leak 알람
- 중대 이상: 진공 인터락, 목표 압력 미도달 또는 안전에 영향을 주는 누설 의심

## 3. 즉시 조치

1. 중대 이상이면 재시작하지 않고 장비를 승인된 절차로 정지합니다.
2. 영향 lot을 SOP-ETCH-20에 따라 hold하고 pump down·압력 원본 trace를 보존합니다.

## 4. Checkpoints

### 4.1 측정과 Pump Down

1. 압력 sensor·gauge의 범위, 영점·교정 이력을 확인합니다.
2. 목표 압력 도달 시간과 곡선을 같은 조건의 이전 run과 비교합니다.

### 4.2 배기·누설·가스 계통

1. Vacuum pump, foreline, valve와 배기 제어 이력을 확인합니다.
2. 승인된 leak check 결과와 밀봉 부위 점검 이력을 확인합니다.
3. 가스 유입량과 차단 상태 이상 여부를 확인합니다.

### 4.3 Chamber와 공통 설비

최근 chamber 개방·부품 교체·PM과 다른 장비의 배기·utility 이상을 확인합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: gauge 이상, pump 성능 저하, valve 문제, 진공 누설, gas 유입, 공통 utility 이상
- 연결 OCAP: PRS, GAS, PM, TMP
- PRS는 공정 중 압력 제어, VAC는 기저 압력·배기·누설을 중심으로 조사합니다.

## 5. Terminator

- 조사 종결: 측정 신뢰성, 배기·누설 상태, 원인 후보와 미확인 사항이 기록됨
- 장비 복귀: 진공 유지·배기 성능의 승인 기준과 SOP-ETCH-01 §4.8 재인증을 만족함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

안전 누설 의심, pump 보호 알람 또는 승인된 leak check 실패는 즉시 설비·EHS와 장비 업체 절차로 올립니다.

## 7. 기록 항목

장비·chamber, run·lot ID, gauge와 측정 범위, base pressure·pump down 시간·곡선 ID, pump·foreline·valve·gas 상태, leak check ID, 기준 run, 원인 후보별 근거, 연결 OCAP, 조치와 승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
