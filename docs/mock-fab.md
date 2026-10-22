# 모의 식각 장비(mock fab)와 Prometheus FDC

**100% 합성 데이터다.** 수치와 임계값은 `data/etch_root_cause_mock_v1`(교육용 합성 데이터셋, 저장소 미포함)에서 역산한 가정이며, 실제 장비 추출값이나 실제 팹 OCAP·FDC 한계가 아니다. 공정 제어, 설비 수리, 실제 Hold/Release 판단에 쓰지 않는다.

## 구성

```text
[AWS EC2]  fab/compose.yaml                                         [로컬]
 etch-01 ┐                                                       backend/prometheus/compose.yaml
 etch-02 ├─HSMS:5000 (docker 내부망만)─▶ collector :80 (HTTP) ◀── Prometheus :9090 (5초 수집)
 etch-03 ┘  S1F3 상태변수 · S5F1 알람 · S6F11 run 이벤트  ├ /             현재 센서값 화면
                                                          ├ /api/current  JSON
                                                          └ /metrics      Prometheus 형식
```

| 위치 | 역할 |
|---|---|
| `fab/sensors.py` | SVID·정상 통계·장비 알람 임계값·고장 프로필, 순수 함수 `run_samples()` |
| `fab/equipment.py` | SECS/GEM 장비(secsgem `GemEquipmentHandler`). 장비 1대 = 프로세스 1개, 챔버별 스레드로 run 무한 반복 |
| `fab/collector.py` | SECS/GEM 호스트(`GemHostHandler`). 5초마다 S1F3 조회, HTTP 화면·JSON·메트릭 제공 |
| `fab/index.html` | 의존성 없는 현재값 화면 |
| `backend/prometheus/` | 로컬 Prometheus 설정·FDC 규칙·대상 주소 |

- **HSMS에는 암호화·인증이 없고 secsgem은 TLS를 지원하지 않는다.** 그래서 HSMS는 docker 내부망에만 두고, 외부에는 collector HTTP 하나만 연다. 공개 GET 전용이며 쓰기 경로는 없다.
- 실제 팹에는 상용 FDC가 이미 있다. 여기의 Prometheus 규칙은 그 **규칙 기반 대역**이며 ML FDC는 만들지 않는다. TRACE의 역할은 FDC 이후의 원인 조사다.

## 데이터 기준 구성

- 장비 3대(ETCH-01~03) × 챔버 2개(CH-A, CH-B) = 공정 모듈 6개, 레시피 1종 `RCP-OX-ETCH-EDU-01`.
- 1 run = 1 Lot. 120초 동안 5초 간격 25샘플을 내며, 관측 웨이퍼는 `<lot>-W01`이다(데이터와 동일).
- run은 쉬지 않고 이어서 24시간 반복한다. Lot ID는 `SIMLOT-<KST 날짜>-<장비 번호><챔버 문자><run 시작 시각>`이다(예: `SIMLOT-20261022-2A151416`). 재시작해도 겹치지 않게 시각을 넣었다. run_no는 장비 단위 카운터라 재시작하면 1101부터 다시 센다.
  - 대기(idle) 상태는 모델링하지 않았다.
- run마다 `FAULT_RATE`(기본 0.1) 확률로 그 챔버의 데이터상 고장 중 하나를 주입한다:

| 챔버 | 고장 후보 |
|---|---|
| ETCH-01/CH-A, ETCH-03/CH-B | HE_LEAK, IGNITION_DELAY, MULTI_FAULT, PRESSURE_DRIFT, RF_SOURCE_LOW |
| ETCH-01/CH-B, ETCH-02/CH-A | MFC_GAS_B_HIGH, OES_DROP, PRESSURE_HIGH, RF_REFLECT, SENSOR_STALE |
| ETCH-02/CH-B, ETCH-03/CH-A | ESC_TEMP_HIGH, MFC_GAS_A_LOW, PRESSURE_OSC, THROTTLE_STUCK |

## SECS/GEM 변수

SVID 번호는 `챔버 대역 + 순번`이다(CH-A 1100번대, CH-B 2100번대). secsgem 내장 SVID 1001~1005와 겹치지 않게 잡았다.

| 순번 | 이름 | 형식 | 단위 |
|---|---|---|---|
| 0~6 | lot_id, wafer_id, recipe_id, recipe_step, process_state, run_no, sample_offset_s | A / U4 | – |
| 10~16 | pressure_sp_mtorr, source_rf_sp_w, bias_rf_sp_w, gas_sf6_sp_sccm, gas_o2_sp_sccm, esc_temp_sp_c, backside_he_sp_torr | F8 | 이름 끝 단위 |
| 20~31 | pressure_pv_mtorr, throttle_valve_pct, source_rf_pv_w, source_rf_reflected_w, bias_rf_pv_w, bias_rf_reflected_w, gas_sf6_pv_sccm, gas_o2_pv_sccm, esc_temp_pv_c, backside_he_pv_torr, chiller_temp_pv_c, oes_intensity_au | F8 | 이름 끝 단위 |
| 40~41 | plasma_detected, sensor_data_quality | U1 / A | – |

- 데이터 trace의 측정 컬럼 21개(설정값 7 + 측정값 12 + 플래그 2)를 전부 대응한다.
- `alert_state`, `ocap_ref`는 판정 결과라서 SVID로 두지 않는다. ALARM은 장비 S5F1으로, WATCH는 Prometheus 규칙으로 판정한다.
- 수집기는 secsgem 내장 SV 1005(AlarmsSet)도 함께 조회해 현재 걸린 알람 목록을 얻는다.
- 수집기에서 끊김이 생겨도 알람 상태를 다시 맞출 수 있다.
- CEID: SVID 대역 + 900 = RUN_START, + 901 = RUN_END (CH-A 2000/2001, CH-B 3000/3001). 리포트에는 컨텍스트 SVID 0~6을 담는다.

## 정상 범위 (NORMAL Lot 3개, 75행)

| 센서 | 설정값 | 평균 | σ | 정상범위(±3σ) | 계통 |
|---|---|---|---|---|---|
| pressure_pv_mtorr | 25 | 25.013 | 0.163 | 24.52~25.50 | vac |
| throttle_valve_pct | – | 44.003 | 0.655 | 42.04~45.97 | vac |
| source_rf_pv_w | 900 | 900.375 | 4.837 | 885.9~914.9 | rf |
| source_rf_reflected_w | – | 5.364 | 0.590 | 4.5(하한)~7.13 | rf |
| bias_rf_pv_w | 120 | 120.134 | 1.448 | 115.8~124.5 | rf |
| bias_rf_reflected_w | – | 2.491 | 0.343 | 2.0(하한)~3.52 | rf |
| gas_sf6_pv_sccm | 100 | 99.975 | 0.429 | 98.69~101.26 | gas |
| gas_o2_pv_sccm | 12 | 11.986 | 0.103 | 11.68~12.30 | gas |
| esc_temp_pv_c | 20 | 19.978 | 0.144 | 19.55~20.41 | esc |
| backside_he_pv_torr | 8 | 7.997 | 0.076 | 7.77~8.22 | esc |
| chiller_temp_pv_c | – | 18.003 | 0.102 | 17.70~18.31 | esc |
| oes_intensity_au | – | 5102.1 | 44.07 | 4970~5234 | plasma |

노이즈는 가우시안이다. 보정이 필요하면 `NOISE_SCALE`(기본 1.0)로 조절한다.

## 고장 프로필

- 데이터와 같이 50초부터 run 끝(120초)까지 목표값으로 선형 램프한다. 연동 센서도 함께 움직인다.

| 고장 | 120초 시점 변화량 |
|---|---|
| PRESSURE_HIGH | 압력 +12, throttle +8 |
| PRESSURE_DRIFT | 압력 +5.4, throttle +4 |
| THROTTLE_STUCK | throttle +52, 압력 +6.3 |
| RF_REFLECT | source 반사파 +78, source RF −45, OES −300 |
| RF_SOURCE_LOW | source RF −155, OES −610 |
| MFC_GAS_A_LOW | SF6 −23, OES −430 |
| MFC_GAS_B_HIGH | O2 +6.2, OES +200 |
| HE_LEAK | He −3.2, ESC +1.7 |
| ESC_TEMP_HIGH | ESC +8.5 |
| OES_DROP | OES −1880 |
| MULTI_FAULT | 압력 +8.2, source 반사파 +48, SF6 −15.6, OES −860 |

- 예외 3종:
  - PRESSURE_OSC: 50초부터 압력 ±3.7, throttle ±5.5로 주기 20초 사인 진동
  - SENSOR_STALE: 55초부터 압력 값 고정, quality `SUSPECT_STALE`
  - IGNITION_DELAY: 40~65초 동안 plasma 0, OES 40~75

## 판정 분리: 장비 = 인터록, Prometheus = FDC

장비는 센서 하나가 하드 리밋을 넘으면 S5F1을 보낸다. 알람 종류는 시나리오와 무관하게 값만으로 정한다. ALID = 챔버 대역 + 400번대 + 순번.

| ALID 순번 | 알람 | 조건 | OCAP |
|---|---|---|---|
| 0 | PRESSURE_HIGH | 압력 ≥ 30 mTorr | OCAP-ETCH-PRS |
| 1 | THROTTLE_SATURATION | throttle ≥ 86 % | OCAP-ETCH-PRS |
| 2 | RF_REFLECT_HIGH | source 반사파 ≥ 37 W | OCAP-ETCH-RF |
| 3 | RF_SOURCE_LOW | source RF ≤ 790 W | OCAP-ETCH-RF |
| 4 | MFC_FLOW_LOW | SF6 ≤ 87 sccm | OCAP-ETCH-GAS |
| 5 | MFC_FLOW_HIGH | O2 ≥ 15 sccm | OCAP-ETCH-GAS |
| 6 | HE_BACKSIDE_LOW | He ≤ 6.1 Torr | OCAP-ETCH-TMP |
| 7 | ESC_TEMP_HIGH | ESC ≥ 25 °C | OCAP-ETCH-TMP |
| 8 | OES_INTENSITY_DROP | OES ≤ 3750 au | OCAP-ETCH-OES |
| 9 | PLASMA_IGNITION_DELAY | 공정 중 plasma 0 | OCAP-ETCH-ARC |

임계값은 데이터에서 같은 센서의 "WATCH 최대값 / ALARM 최소값" 경계를 역산한 값이다.
- 반사파는 34.8~39.4 사이가 비어 있어 37로 정했다.
- OES는 3712~3805 사이가 비어 있어 3750으로 정했다.

`ocap` label에는 저장소 `sop-ocap/` 문서 ID를 쓴다. 데이터셋의 가상 키(`OCAP-VAC-01` 등 8개)는 실제 문서와 연결되지 않으므로 쓰지 않는다. 대응은 각 문서의 "언제 여는가"를 기준으로 했다:

| 경보 | 문서 |
|---|---|
| PRESSURE_HIGH, THROTTLE_SATURATION, PRESSURE_TREND, PRESSURE_OSC | OCAP-ETCH-PRS (공정 압력·throttle). OCAP-ETCH-VAC는 기저 압력·누설용이라 쓰지 않음 |
| RF_REFLECT_HIGH, RF_SOURCE_LOW | OCAP-ETCH-RF |
| MFC_FLOW_LOW, MFC_FLOW_HIGH | OCAP-ETCH-GAS |
| HE_BACKSIDE_LOW, ESC_TEMP_HIGH | OCAP-ETCH-TMP (He 후면 냉각·온도). OCAP-ETCH-ESC는 흡착·dechuck용 |
| OES_INTENSITY_DROP | OCAP-ETCH-OES |
| PLASMA_IGNITION_DELAY | OCAP-ETCH-ARC |
| SENSOR_STALE, MULTIVARIATE_FDC | SOP-ETCH-12 (해당 OCAP 없음, 공통 이상 대응 절차) |

FDC_WATCH는 센서 계통에 따라 위 문서를 쓴다: vac → PRS, rf → RF, gas → GAS, esc → TMP, plasma → OES.

Prometheus 규칙(`backend/prometheus/rules.yml`)은 장비가 보지 못하는 것을 잡는다:

| 규칙 | 식 요지 | 장비 알람으로 안 되는 이유 |
|---|---|---|
| FDC_WATCH | \|값 − 평균\| > 3σ, 15초 지속 | 하드 리밋보다 먼저 경고 (데이터에서도 WATCH가 ALARM보다 25~70초 앞섬) |
| PRESSURE_TREND | `predict_linear(압력[60s], 60) >= 30` 이면서 현재 < 30 | 장비는 현재 값만 봄 |
| PRESSURE_OSC | `stddev_over_time(압력[40s]) > 1` 이면서 `abs(deriv) < 0.05` | 리밋을 넘지 않아 장비는 끝까지 모름 |
| SENSOR_STALE | `changes(측정값[20s]) == 0` | 장비는 자기 센서가 멈춘 걸 모름 |
| MULTIVARIATE_FDC | WATCH가 서로 다른 계통(vac·rf·gas·esc) 2개 이상에서 동시 발생 | 시계열을 조합해야 판정 가능 |
| EQUIPMENT_ALARM | `etch_alarm_active == 1` | 장비 알람을 같은 API로 모으기 위함 |

- 원본 데이터에서 PRESSURE_TREND, SENSOR_STALE, MULTIVARIATE_FDC는 장비 알람이었다. 여기서는 FDC 쪽으로 옮겼다. 데이터와 의도적으로 다른 부분이다.
- OES는 다른 고장에도 함께 떨어지므로 MULTIVARIATE 계통 수에서 뺀다.

## 메트릭

| 메트릭 | label | 내용 |
|---|---|---|
| `etch_sensor_value` | tool, chamber, sensor | 측정값 12개 + plasma_detected |
| `etch_setpoint` | tool, chamber, sensor | 레시피 설정값 7개 |
| `etch_sensor_normal_mean`, `etch_sensor_normal_sd` | sensor, subsystem, unit, ocap | 위 정상 통계 (규칙의 단일 출처) |
| `etch_data_quality_good` | tool, chamber | 1 = GOOD |
| `etch_run_info` | tool, chamber, lot_id, wafer_id, recipe_id, run_no | 현재 run 컨텍스트, 값 1 |
| `etch_sample_offset_seconds` | tool, chamber | run 경과 초 |
| `etch_alarm_active` | tool, chamber, alarm, ocap | 장비 알람 0/1 |
| `etch_equipment_up` | tool | HSMS 통신 여부 |

- lot_id는 `etch_run_info`에만 둔다. 센서 시계열에 붙이면 label 조합이 run마다 늘어나기 때문이다.
- Lot과 센서값은 이렇게 결합한다: `etch_sensor_value * on(tool,chamber) group_left(lot_id, wafer_id) etch_run_info`.
- 주입한 고장 시나리오(정답 라벨)는 노출하지 않는다. 데이터 README의 "에이전트 입력에 넣지 않음" 원칙과 같다.

## 후속: TRACE로 신호 전달 (미구현)

장비 알람과 FDC 경고는 모두 Prometheus `GET /api/v1/alerts`에 같은 형태로 모인다. 후속 Python 소비자는 다음 둘 중 하나를 하면 된다:
- 이 API를 폴링한다.
- Alertmanager webhook을 받는다.

받은 신호는 아래 통합 이벤트로 바꿔 LangChain 에이전트를 실행한다:

```json
{"source": "equipment|fdc", "tool_id": "ETCH-01", "chamber_id": "CH-B", "lot_id": "SIMLOT-20261022-1B100000",
 "wafer_id": "SIMLOT-20261022-1B100000-W01", "rule": "PRESSURE_HIGH", "value": 30.1, "threshold_or_baseline": 30,
 "unit": "mTorr", "ocap_ref": "OCAP-ETCH-PRS", "state": "set|clear", "event_time": "2026-10-22T10:00:00+09:00"}
```

근거 시계열은 Prometheus `query_range`로 알람 전후 구간을 조회한다.

## 실행

### 다른 컴퓨터에서 Prometheus로 보기

AWS 수집기는 공개 HTTP라 인증·키 없이 수집할 수 있다. 대상 주소(`backend/prometheus/targets.json`)와 규칙이 저장소에 들어 있으므로, Docker가 있는 컴퓨터라면 아래만 하면 된다.

```bash
git clone https://github.com/meotjin-girl/etch-trace.git && cd etch-trace
git checkout feature/mock-fab        # develop에 머지되기 전까지
docker compose -f backend/prometheus/compose.yaml up -d
```

| 확인 | 위치 | 정상 |
|---|---|---|
| 장비 화면 (브라우저만 있으면 됨) | http://32.236.188.208/ | 카드 6장이 5초마다 갱신 |
| 수집 대상 | http://127.0.0.1:9090/targets | `mock-fab` 대상이 `UP` |
| 센서 추이 | http://127.0.0.1:9090/graph, 식 `etch_sensor_value{sensor="pressure_pv_mtorr"}` | 6개 선이 25 근처 |
| 경보 | http://127.0.0.1:9090/alerts | 고장 run 중 `EQUIPMENT_ALARM`·`FDC_*` 발생 |

- Prometheus는 컴퓨터마다 따로 돈다. **기록은 각자 켠 시점부터 쌓이며**, 다른 컴퓨터나 켜기 전 데이터는 받을 수 없다. 장비 쪽에는 이력이 남지 않는다. 보존 기간은 15일이며 docker 볼륨 `prometheus_prometheus-data`에 저장된다.
- 9090 포트는 `127.0.0.1`에만 열린다. 같은 네트워크의 다른 사람이 내 Prometheus를 볼 수는 없다.
- 규칙이나 대상 파일을 고친 뒤에는 `docker compose -f backend/prometheus/compose.yaml restart`를 실행한다.
- 끄기: `docker compose -f backend/prometheus/compose.yaml down` (기록까지 지우려면 `down -v`).
- 대상이 `DOWN`이면 다음 순서로 확인한다.
  1. 브라우저로 http://32.236.188.208/metrics 가 열리는지 본다. 안 열리면 EC2·보안그룹(80) 문제다.
  2. 열리는데도 DOWN이면, 사내망 등에서 외부 80 포트가 막혔는지 확인한다.
  3. EC2 공인 IP가 바뀌면 `targets.json` 한 줄만 고친다. Elastic IP를 쓰면 바뀌지 않는다.

### 개발·배포

```bash
# 단위·HSMS 테스트
(cd fab && uv sync --group dev && uv run pytest)
# FDC 규칙 테스트
(cd backend/prometheus && docker run --rm -v "$PWD":/w -w /w --entrypoint promtool prom/prometheus:v2.53.0 test rules rules_test.yml)

# 로컬에서 장비+수집기 실행 → http://localhost:8080
docker compose -f fab/compose.yaml up -d --build

# AWS 배포 (ubuntu@32.236.188.208, 키는 저장소 루트 skala-key.pem, gitignore 대상)
rsync -az --delete --exclude .venv --exclude __pycache__ --exclude .env -e "ssh -i skala-key.pem" fab/ ubuntu@32.236.188.208:~/fab/
ssh -i skala-key.pem ubuntu@32.236.188.208 'cd fab && sudo docker compose up -d --build'
```

- 서버 설정은 EC2의 `~/fab/.env`에 있으며 git에는 없다. 현재 값은 `FAB_PORT=80`, `FAULT_RATE=0.2`이다. 값을 바꾸면 `sudo docker compose up -d`로 반영한다.
- 위 rsync는 `--exclude .env`로 서버 설정을 보존한다. 이 옵션이 없으면 `--delete`가 서버의 `.env`를 지운다.
- 메트릭 label(예: `ocap`)과 규칙을 함께 바꿀 때는 **Prometheus를 먼저 재시작하고, 그다음 장비를 재배포**한다.
  - 순서가 반대면 재시작 전에 수집된 옛 label 시계열이 만료 표시 없이 최대 5분 남는다.
  - 그동안 `etch:sensor_zscore`가 duplicate series 에러를 내고 FDC_WATCH·MULTIVARIATE_FDC가 멈춘다. 5분이 지나면 저절로 풀린다.
