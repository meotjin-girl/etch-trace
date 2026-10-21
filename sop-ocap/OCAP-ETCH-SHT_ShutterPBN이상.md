# OCAP-ETCH-SHT Shutter·PBN 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Shutter·PBN이 있는 Ion Mill |
| 공정·감시 항목 | shutter position·상태 전환, PBN gas·제어 신호 |
| 필요 데이터 | recipe·step별 예상 상태, 명령·feedback 태그, PBN·Ar flow, beam, event·PM 이력 |
| 검증 가능 범위 | PHM 태그 일부 분석 가능. 실제 개폐와 구동 상태는 현장 점검 필요 |

## 2. Activator

- 경고: 같은 step 대비 shutter 전환 시간 또는 PBN 신호의 지속 편차
- 이상: 예상 shutter 상태와 feedback 불일치, 허용되지 않은 전환 또는 PBN 관리 한계 이탈
- 중대 이상: shutter 인터락 또는 wafer가 비정상 beam에 노출될 가능성

## 3. 즉시 조치

1. 중대 이상이면 beam 운전을 중지하고 승인된 장비 정지 절차를 따릅니다.
2. 영향 run·lot을 hold하고 shutter 명령값과 실제 feedback을 구분해 보존합니다.

## 4. Checkpoints

### 4.1 Shutter 상태와 전환

1. Step별 예상 shutter 상태와 기록값을 비교합니다.
2. Beam 안정화·식각 시작·종료 구간의 전환 시점을 확인합니다.

### 4.2 PBN·Beam·Gas

PBN gas readback, beam voltage·current와 Ar 공급의 시점별 연관성을 확인합니다.

### 4.3 같은 조건과 정비 이력

동일 recipe·step의 정상 shutter·PBN 기록과 구동부·PBN PM·event를 확인합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: recipe sequence 차이, shutter 구동·상태 감지 문제, PBN 공급·제어 문제
- 연결 OCAP: BEAM, GAS, MOTION, PM
- 태그가 명령값인지 실제 위치 feedback인지 확인하고, 상태값만으로 물리적 개폐를 확정하지 않습니다.

## 5. Terminator

- 조사 종결: 예상·실제 상태, 관련 beam·gas와 원인 후보가 기록됨
- 장비 복귀: shutter·PBN 운전이 승인 기준에 부합하고 필요한 재인증을 완료함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

실제 위치 feedback 부재, 인터락 또는 비정상 beam 노출 가능성은 설비 파트장과 장비 업체, 품질 담당에게 올립니다.

## 7. 기록 항목

장비·recipe·step, run·lot ID, shutter 예상 상태·명령·feedback·전환 시각, PBN·Ar·beam 값, event·PM, 기준 run, 원인 후보별 근거, 현장 점검·품질 확인·조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
