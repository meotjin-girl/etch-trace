# OCAP-ETCH-ARC 플라즈마 점화 실패·아크 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | 아크 감시 기능이 있는 RF Plasma Etch |
| 공정·감시 항목 | ignition failure, plasma loss, arc detection, RF 전원 인터락 |
| 필요 데이터 | 장비 event log, recipe·step, RF forward/reflected·match, gas·pressure, PM·부품 이력, 영향 lot |
| 검증 가능 범위 | 현재 PHM 데이터로 직접 분석 불가. event log와 승인된 안전 점검 필요 |

## 2. Activator

- 이상: Plasma Ignition Failure 또는 점화 후 Plasma Loss
- 중대 이상: Arc Detection, 반복 아크, RF 전원·절연 관련 인터락

아크는 일반 통계 편차보다 높은 우선순위의 장비 보호·안전 절차를 적용합니다.

## 3. 즉시 조치

1. 아크·전원 인터락이면 재점화하지 않고 승인된 장비 정지·격리 절차를 따릅니다.
2. 작업자와 engineer에게 통보하고 영향 run·lot을 hold합니다.
3. 임의로 인터락을 해제하거나 반복 재시작하지 않습니다.

## 4. Checkpoints

### 4.1 이벤트와 시점

점화 실패, 점화 후 소멸, 반복 아크를 구분하고 recipe·step·전원 전환 시점을 확인합니다.

### 4.2 관련 운전 조건

1. RF power, reflected power, match 상태와 오류를 확인합니다.
2. 점화 시 pressure·gas 조건이 승인 범위인지 확인합니다.
3. 인터락과 전원 event log의 선후관계를 보존합니다.

### 4.3 정비·부품과 영향 범위

RF 부품, chamber 절연 부위, 최근 PM 이력을 확인하고 처리 중단 run·lot의 후속 검사를 지정합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: RF 점화·전달 이상, gas·pressure 조건 문제, 내부 방전·절연 계통 문제, 설정 차이
- 연결 OCAP: RF, PRS, GAS, PM
- 물리 원인은 제조사 승인 안전 점검 전까지 확인된 원인으로 기록하지 않습니다.

## 5. Terminator

- 조사 종결: 이벤트 유형·시점, 영향 범위와 원인 후보가 기록됨
- 장비 복귀: 승인된 안전 점검, 재기동 검증과 SOP-ETCH-01 §4.8 재인증을 완료함
- Lot 처분: 품질 확인 후 SOP-ETCH-20으로 별도 승인함

## 6. 에스컬레이션

아크, 탄화·연기·냄새, 반복 점화 실패 또는 전기적 손상 의심은 즉시 EHS·설비 파트장·장비 업체로 올립니다. 현장 비상 절차가 우선합니다.

## 7. 기록 항목

장비·chamber·recipe·step, run·lot ID, 이벤트 코드·시각·유형, RF·match·gas·pressure 값, event log ID, PM·부품 이력, 원인 후보별 근거, 안전 점검·재기동·품질 확인과 승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
