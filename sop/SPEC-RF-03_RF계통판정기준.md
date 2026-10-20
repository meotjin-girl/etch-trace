# SPEC-RF-03 RF 계통 판정 기준

| 항목 | 내용 |
|---|---|
| 문서 ID | SPEC-RF-03 |
| 개정 | Rev 0.1 (예시, 2026-10-20) |
| 문서 유형 | 판정 기준서(SPEC) |
| 적용 장비 | 플라즈마 식각 장비 RF generator · match network |
| 관련 문서 | SOP-ETCH-12, SOP-SAFE-01, WI-PM-07 |

> `[예시]` 수치는 시연용이다.

## 1. 목적과 범위

RF 전력 전달 계통(generator → 케이블 → match network → 전극)이 정상인지 판정하는 기준과, 기준을 벗어났을 때의 점검 순서를 정한다. reflected power가 커지면 플라즈마에 전달되는 전력이 줄어 etch rate·균일도가 바뀌고, generator와 전송선이 과열되며, 플라즈마가 불안정해지거나 꺼질 수 있다.

## 2. 판정 기준

### 2.1 감시 항목

forward power, reflected power, match tune/load 커패시터 위치, (있으면) Vdc·Vpp. 모두 recipe step별로 본다.

### 2.2 정상 범위

| 항목 | 정상 | 주의 | 이상 |
|---|---|---|---|
| reflected / forward | `[예시]` 2% 미만 | 2~5% | 5% 이상 또는 인터락 |
| reflected (기준 run 대비) | 중앙값 +20% 미만 | +20~50% | +50% 이상 |
| tune/load 위치 (기준 run 대비) | 기준 범위 안 | 한쪽 끝으로 치우침 | 끝단 도달(튜닝 여유 없음) |

기준 run은 SOP-ETCH-12 §4.3으로 고른다.

### 2.3 제외 구간

플라즈마 점화 직후와 step 전환 직후 `[예시]` 2초는 match가 튜닝 중이므로 판정에서 뺀다. 펄스 RF recipe는 기계식 튜닝이 펄스를 따라가지 못해 reflected 값이 들쭉날쭉할 수 있으므로, 펄스 recipe는 같은 펄스 recipe 기준 run끼리만 비교한다.

### 2.4 반복 상승 시 점검

Reflected power 상승이 반복될 경우 match network 접점과 calibration 상태를 확인한다.

- "반복"은 같은 챔버·같은 recipe step에서 §2.2 주의 이상이 연속 3 run `[예시]` 또는 24시간 `[예시]` 안에 5 run 이상 나온 경우다.
- 점검은 §3 순서를 따른다.

### 2.5 즉시 정지 조건

아래는 조사 전에 장비를 멈춘다 (SOP-ETCH-12 §4.1).

- reflected power 인터락 발생
- 아크 감지
- match가 끝단에 걸려 튜닝이 되지 않음

## 3. 점검 순서

장비를 열지 않는 점검부터 한다.

1. **설정:** 해당 recipe의 match preset, 튜닝 모드가 표준값인지 확인한다. 최근 recipe 변경 이력을 본다.
2. **이력:** 마지막 RF calibration 날짜, 마지막 PM 날짜, reflected 상승이 시작된 시점과 PM·부품 교체 시점의 선후를 본다.
3. **calibration:** generator 출력과 reflected 측정 calibration을 확인한다.
4. **접점·케이블:** SOP-SAFE-01 LOTO 후 match 출력 접점, RF 스트랩, 케이블 커넥터의 변색·마모·토크를 확인한다.
5. **match 내부:** 가변 커패시터와 스텝 모터의 마모·이동 범위를 확인한다.
6. **기준 비교:** 플라즈마 없이 전압·전류·위상을 측정해 정상 장비 기준과 비교한다. VSWR(또는 return loss)만으로 판단하지 말고 insertion loss를 함께 기록한다. 임피던스가 커지면 reflected가 오히려 낮아 보일 수 있기 때문이다.

## 4. 기록

- 이상 run ID, step, reflected/forward 값(W)과 기준 대비 차이
- 점검 단계별 결과, 교체 부품, calibration 전후 값
- insertion loss·VSWR 측정값

## 5. 개정 이력

| Rev | 날짜 | 내용 |
|---|---|---|
| 0.1 | 2026-10-20 | 예시 초안. `db/documents.json`의 §2.4 문장 유지 |
