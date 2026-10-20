# OCAP-ETCH-ESC 정전척 흡착·Dechuck 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | ESC를 사용하는 Plasma Etch |
| 공정·감시 항목 | chuck·dechuck, ESC voltage·current, wafer 고정, 관련 인터락 |
| 필요 데이터 | ESC·He cooling, wafer 검사, robot·aligner·lift pin log, chuck PM·세정, 영향 lot |
| 검증 가능 범위 | 현재 PHM 데이터로 직접 분석 불가. 장비 log·wafer 검사와 제조사 승인 점검 필요 |

## 2. Activator

- 이상: 흡착 실패, 유지 불량, 분리 실패 또는 ESC 신호 관리 한계 이탈
- 중대 이상: wafer 고정 실패·파손 가능성 또는 관련 인터락

## 3. 즉시 조치

1. 중대 이상이면 wafer를 임의 반송하지 않고 승인된 장비 복구 절차를 따릅니다.
2. 영향 run·lot을 hold하고 ESC·반송 event log를 보존합니다.
3. 제품 손상과 작업자 위험 가능성을 engineer에게 즉시 통보합니다.

## 4. Checkpoints

### 4.1 이벤트와 ESC 신호

흡착 실패·유지 불량·분리 실패를 구분하고 ESC 전압·전류, 설정값과 알람을 확인합니다.

### 4.2 냉각·Wafer·반송

1. He backside pressure·flow 변화를 확인합니다.
2. Wafer 파손·휨·오염과 앞·뒷면 검사 결과를 확인합니다.
3. Robot·aligner·lift pin log의 선후관계를 확인합니다.

### 4.3 Chamber와 PM

ESC 접촉면 세정·정비와 최근 PM, 제품 손상·파티클·온도 이상 후속 검사 필요성을 확인합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: ESC 전원·흡착 제어, wafer 상태, 접촉면 오염, 반송 계통 문제
- 연결 OCAP: TMP, DEF, UNI, PM
- 제조사 승인 점검 전에는 ESC 물리 고장을 확정하지 않습니다.

## 5. Terminator

- 조사 종결: 이벤트 유형, 영향 범위와 원인 후보가 기록됨
- 장비 복귀: 제조사 승인 점검과 wafer 처리 안정성·품질 재인증을 완료함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

wafer 파손·stuck wafer·반송 충돌 또는 고전압 계통 이상은 즉시 설비 파트장·EHS·장비 업체로 올립니다.

## 7. 기록 항목

장비·chamber·recipe·step, run·lot·wafer ID, 이벤트 유형·코드·시각, ESC·He 값, wafer 검사, 반송 log, PM 이력, 원인 후보별 근거, 현장 점검·품질 확인·조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
