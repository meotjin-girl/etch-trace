# OCAP-ETCH-BEAM 이온 빔 전압·전류 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch설비기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | Ion Mill |
| 공정·감시 항목 | beam voltage·current, 설정값·실제값 차이, 안정성 |
| 필요 데이터 | recipe·step, beam·suppressor 시계열, Ar flow, source usage, PM·교체 이력 |
| 검증 가능 범위 | PHM 센서값으로 직접 추세 분석 가능. 고장 부품 확정에는 event log와 현장 점검 필요 |

## 2. Activator

- 경고: 같은 recipe·step 대비 beam 전압·전류의 지속 편차 또는 변동성 증가
- 이상: 설정값과 실제값의 관리 한계 이탈 또는 beam current 불안정
- 중대 이상: Beam Voltage/Current 인터락 또는 beam 유지 실패

## 3. 즉시 조치

1. 중대 이상이면 승인된 장비 정지 절차를 따르고 재시작하지 않습니다.
2. 영향 run·lot을 SOP-ETCH-20에 따라 hold하고 센서 원본을 보존합니다.

## 4. Checkpoints

### 4.1 설정과 시계열

1. Recipe·step의 목표 beam voltage·current와 변경 이력을 확인합니다.
2. 두 신호의 변화 방향, 편차 구간과 변동성을 함께 비교합니다.
3. 점화·안정화·step 전환 과도 구간과 정상 운전 구간을 구분합니다.

### 4.2 관련 계통

Ar 유량, suppressor 전압·전류와의 동반 변화, source 누적 사용량과 PM·교체 이력을 확인합니다.

### 4.3 같은 조건 비교

동일 장비·recipe·step의 대상 이전 정상 run 및 승인된 과거 사례와 비교합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: recipe 설정 차이, beam 전원 계통, Ar 공급 변화, source 상태 변화, grid·suppressor 이상
- 연결 OCAP: GRID, GAS, VAC, PM
- 센서 연관성만으로 source나 grid 고장을 확정하지 않습니다.

## 5. Terminator

- 조사 종결: 편차 구간, 관련 신호, 원인 후보와 미확인 사항이 기록됨
- 장비 복귀: beam 신호가 승인 기준 안이고 제조사 검증 및 SOP-ETCH-01 §4.8 재인증을 완료함
- Lot 처분: SOP-ETCH-20에 따라 별도로 승인함

## 6. 에스컬레이션

인터락, 전원 불안정 또는 source·grid 손상 의심은 설비 파트장과 장비 업체로 올립니다. 품질 영향은 공정·품질 담당에게 올립니다.

## 7. 기록 항목

장비·recipe·step, run·lot ID, beam 설정·실제 전압·전류와 단위, 편차 구간·변동성, Ar·suppressor·source usage, 기준 run, 원인 후보별 근거, 연결 OCAP, 조치·검증·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
