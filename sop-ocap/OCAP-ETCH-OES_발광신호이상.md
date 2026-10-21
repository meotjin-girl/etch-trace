# OCAP-ETCH-OES 플라즈마 발광 신호 이상 대응

| 담당 팀 | 버전 | 최근 개정 |
| --- | --- | --- |
| Etch공정기술팀 | 1.0 | 2026-10-20 |

## 1. 적용 범위

| 항목 | 내용 |
| --- | --- |
| 장비 유형 | OES가 장착된 Plasma Etch |
| 공정·감시 항목 | 파장별 세기·비율·형상, SNR, drift, OES alarm |
| 필요 데이터 | wavelength·channel·노출 조건, spectrum 시계열, recipe·step, RF·gas·pressure, window·광학계 PM, endpoint·품질 |
| 검증 가능 범위 | 현재 PHM 데이터로 직접 분석 불가. OES 원본과 광학계 점검 필요 |

## 2. Activator

- 경고: OES 세기·비율 또는 SNR의 지속 drift
- 이상: 승인된 관리 한계 밖의 신호 세기·형상 또는 OES alarm
- 중대 이상: 신호 상실로 endpoint·공정 제어 신뢰성을 확보할 수 없음

## 3. 즉시 조치

1. 원본 spectrum과 노출·gain·channel 설정을 보존합니다.
2. Endpoint에 사용되는 신호가 상실되면 해당 run·lot을 hold하고 후속 투입을 중지합니다.

## 4. Checkpoints

### 4.1 관측 조건과 신호

1. 파장·channel, 노출·gain, recipe·step 일치 여부를 확인합니다.
2. 세기, SNR, spectrum 형상과 시간 변화를 비교합니다.

### 4.2 광학 경로와 공정 조건

1. Window cleaning, 광섬유·검출기 상태와 교정 이력을 확인합니다.
2. RF, gas flow, chamber pressure의 동반 변화를 확인합니다.
3. 마지막 PM·window cleaning 전후를 비교합니다.

### 4.3 품질·과거 신호

Endpoint·etch rate와 같은 품질 지표 및 같은 파장·recipe·step의 이전 신호를 비교합니다.

### 4.4 원인 후보와 추가 검증

- 원인 후보: 광학 설정 문제, window 오염, 광학 측정 계통 이상, plasma·gas·공정 조건 변화
- 연결 OCAP: EPD, RF, GAS, PRS, PM
- OES는 관측 신호 자체, EPD는 종료 시점 판정을 중심으로 조사합니다.

## 5. Terminator

- 조사 종결: 관측 조건, 신호 품질, 공정 연관성과 원인 후보가 기록됨
- 장비 복귀: 광학 신뢰성과 공정 감시 기능이 승인 기준 안이고 필요한 재인증을 완료함
- Lot 처분: endpoint·품질 영향에 따라 SOP-ETCH-20으로 별도 승인함

## 6. 에스컬레이션

신호 상실, 교정 실패 또는 endpoint 신뢰성 상실은 공정·설비 담당과 장비 업체로 올립니다.

## 7. 기록 항목

장비·chamber·recipe·step, run·lot ID, wavelength·channel·노출·gain, 신호 세기·비율·SNR·spectrum ID, RF·gas·pressure, 광학 PM, 기준 run, 원인 후보별 근거, 연결 OCAP, 조치·승인.

## 8. 개정 이력

| 버전 | 날짜 | 변경 내용 | 검토·승인 |
| --- | --- | --- | --- |
| 1.0 | 2026-10-20 | 제정 | 현장 검토 전 |
