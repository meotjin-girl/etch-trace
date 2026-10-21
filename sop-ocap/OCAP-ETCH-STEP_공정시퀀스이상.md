# OCAP-ETCH-STEP 공정 Step 지속 시간·시퀀스 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Plasma Etch / Ion Mill |
| 공정·감시 항목 | step duration, 실행 순서, timeout, sequence error, 종료 조건 |
| 필요 데이터 | 승인 recipe 버전·step 목록, 실행 event log, step별 시간, endpoint·interlock, beam/RF/gas/pressure, 변경 이력 |
| 검증 가능 범위 | PHM step 기록 일부 분석 가능. 제어 logic 원인은 software·장비 log 추가 확인 필요 |

## 2. Activator

- 경고: 동일 recipe·step 대비 지속 시간이 주의 한계를 벗어나거나 증가 추세임
- 이상: 비정상 step duration, 승인 순서와 다른 실행 또는 재시도·정지 발생
- 중대 이상: Step Timeout, Sequence Error 또는 장비 보호 인터락

## 3. 즉시 조치

1. 중대 이상이면 자동 재시작하지 않고 승인된 장비 정지 절차를 따릅니다.
2. 영향 run·lot을 hold하고 recipe 버전과 전체 event log를 보존합니다.

## 4. Checkpoints

### 4.1 Recipe와 실행 시간

1. 승인 recipe 버전과 step 목록·순서를 확인합니다.
2. Step별 실제 지속 시간을 동일 조건의 대상 이전 run과 비교합니다.
3. 시간 고정, endpoint, event 조건 등 종료 방식을 구분합니다.

### 4.2 Event와 관련 신호

1. 중단·재시도·일시 정지·인터락의 선후관계를 확인합니다.
2. 시간 편차 구간의 beam/RF/gas/pressure 변화를 확인합니다.
3. Recipe, software와 장비 설정 변경 이력을 확인합니다.

### 4.3 품질 영향

처리 시간이 달라진 wafer·lot과 필요한 품질 검사를 지정합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: recipe sequence 차이, 장비 event 지연, 종료 조건 변화, 제어 계통 문제
- 연결 OCAP: EPD, BEAM, GAS, PRS, ARC, PM
- 시간 편차만으로 software 또는 특정 계통 고장을 확정하지 않습니다.

## 5. Terminator

- 조사 종결: 실행 이력, 종료 방식, 관련 신호, 영향 범위와 원인 후보가 기록됨
- 장비 복귀: 승인 recipe와 step 실행 검증 및 필요한 품질 재인증을 완료함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

Sequence Error, 반복 timeout, recipe 무결성 또는 software 변경 의심은 공정·설비·자동화 담당과 장비 업체로 올립니다.

## 7. 기록 항목

장비·chamber·recipe 버전·step, run·lot ID, 예상·실제 순서와 시간, 종료 방식, event·interlock, 관련 sensor, 변경 이력, 기준 run, 원인 후보별 근거, 연결 OCAP, 품질 확인·조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
