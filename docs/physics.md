# TRACE Physics v1

Physics v1은 TCAD에서 영감을 받은 **0차 물리 관계식 검증 계층**이다. RAG나
엔지니어 판단을 대체하지 않는다. 사용자가 명시한 계측값만 사용해 계산값,
입력값, 단위, 출처, 가정과 부족 데이터를 결과에 보존한다.

## 구현 범위

| 모델 | 관계식 | 필수 입력 | 결과 |
|---|---|---|---|
| 일정 속도 식각 깊이 | `D = R × t` | `etch_rate_nm_min`, `etch_time_sec` | `expected_etch_depth_nm` |
| 평균 식각 속도 | `R = (D0 - D1) / t` | `pre_thickness_nm`, `post_thickness_nm`, `etch_time_sec` | `average_etch_rate_nm_min` |
| 선택비 | `S = R_target / R_mask` | `target_etch_rate_nm_min`, `mask_etch_rate_nm_min` | `selectivity_ratio` |

`mcp/physics_models.py`가 순수 계산과 검증을 소유하고 `mcp/physics.py`가
`evaluate_etch_physics` MCP 도구를 공개한다. 단일 ReAct Agent는 필요할 때 이 도구를
호출하고 결과의 `calculated`, `needs_more_data`, `invalid_input`을 구분해 인용한다.
계산 불가는 사례·문서 조사를 중단시키지 않는다.

`endpoint_sec`는 전체 식각 시간이 아니므로 `etch_time_sec`로 재사용하지 않는다.
계산 예상 깊이는 실측 깊이로 표시하지 않는다. 계산 결과만으로 고장 원인 확정,
Recipe 변경 또는 Lot hold/release를 수행하지 않는다.

## 데이터 경계

Agent는 사용자가 명시한 `nm`, `nm/min`, 초·분 단위 물리 입력만 도구 인자로 넘긴다.
사용자 입력의 출처는 `user_input`이며, 향후 설비 로그 연결 시 `equipment_log`,
계측 시스템 연결 시 `metrology`처럼 원본 출처를 보존해야 한다.

`fab/`의 합성 장비는 120초 run, `sample_offset_s`, RF·가스·압력·온도 센서를
제공한다. Sensor MCP는 `FAB_COLLECTOR_URL`이 설정된 경우 collector의 `/api/runs`에서
이 데이터를 읽지만, 전후 막 두께와 실측 식각 속도는 제공되지 않는다. 따라서 run
시작·종료 이벤트로 확인한 시간만 `equipment_log` 출처로 사용하며 샘플 offset을
임의로 완료 시간으로 간주하지 않는다.

도구 결과는 모델·버전·수식·입력·출처·결과·가정·부족 항목·경고를 담는다. 현재 Agent
Server 경로에서는 결과가 thread 대화에 남고, 후보의 근거 설명(`rationale`)에 인용된다.
업무 조사에는 계산 결과 전용 필드가 없다. 레거시 v1 보고서는 `physicsResults` 등
별도 필드로 저장했다(`backend/v1_models.py`).

## 향후 확장 백로그

다음은 Physics v1에서 의도적으로 제외한다. 실제 데이터 계약, 검증 기준과 별도
모델 버전을 마련한 뒤 확장한다.

- 플라즈마 sheath 해석과 이온 에너지·각도 분포
- 반응종 수송과 Arrhenius 온도 의존성
- RF matching 회로 모델
- chamber conductance와 pumping 모델
- 보정·검증된 microloading, ARDE/RIE lag 예측
- 실제 패턴 CD/profile 및 공간 식각 균일도 예측
- 다중 Recipe Step 시간 적분
- 측정·모델 불확실성 전파
- 사례가 없는 조사에서 센서·물리 근거의 신뢰도에 따라 탐색 범위를 확장하는 정책
- 자동 Recipe 변경과 자동 Lot hold/release

Physics v1은 인과 모델이나 고장 분류기가 아니다. 계산된 일관성 또는 편차는 원인
후보를 지지·반박하는 보조 근거이며 센서, 정비, MES, 계측 원본과 엔지니어 승인이
필요하다.

## Physics v2 정량 분석

v1 도구 계약은 그대로 유지한다. v2 결과(레거시 보고서의 `quantitativeResults`,
`sensorAnalysis`)는 계산 성공 여부, 값의 출처, 현장 검증 상태를 다음처럼 분리한다.

- `status`: `CALCULATED`, `INSUFFICIENT_DATA`, `INVALID_INPUT`
- `value_origin`: `MEASURED`, `CALCULATED`, `SIMULATED`
- `validation_status`: `VALIDATED`, `NOT_VALIDATED`

| Tool | 해결하는 문제 | 계산하지 않는 것 |
|---|---|---|
| `evaluate_etch_physics` | 예상 깊이, 실측 평균 속도, 선택비 | 설비 고장·자동 조치 |
| `compare_reference_runs` | 이전 동일 조건 정상 Run의 평균·표준편차·편차·z-score | 미래/비교 불가 Run 사용, 무승인 합격 판정 |
| `integrate_etch_rate_series` | 명시된 구간별 `R(t)`의 누적 제거 깊이 | 센서값으로 식각률 생성 |
| `compare_metrology_to_spec` | 실측값과 목표·승인 규격의 절대/상대 오차 | 계측 또는 승인 규격이 없을 때 판정 |
| `analyze_sensor_timeseries` (Sensor MCP) | 최초 이상, 범위, setpoint 편차, 지속시간, 동반 센서, 알람·OCAP | 동시 변화만으로 인과관계 확정 |
| `simulate_educational_etch` | 가정 계수 기반 상대 식각률·ARDE 깊이·직사각형 2D 도식 | 검증 예측, Bowing·Taper·원인 판정 |

Mock Fab collector는 메모리 내 최근 200개 Run을 `/api/runs`로 제공한다. Run에는
장비·chamber·recipe·step·시작/종료 시각·5초 샘플·알람·품질 상태가 포함된다.
Sensor MCP는 대상보다 먼저 종료된 동일 조건 `normal_candidate`만 기준 Run으로
사용한다. 최소 3건이 없으면 기준 비교는 `INSUFFICIENT_DATA`다. 이 이력은 합성 데모이고
collector 재시작 시 사라진다.

Mock Fab의 ±3σ와 장비 알람 임계값은 합성 기준이다. 승인된 제품 관리 규격이 아니며
합격·불합격에 사용하지 않는다. 규격 판정은 승인 여부, 문서 ID, revision, 단위가 있는
구조화 `ControlLimit`에만 허용된다.

## Level 1~3 교육용 시뮬레이션

실제 조사 계산과 교육용 시뮬레이션은 구분한다(레거시 보고서에서는
`educationalSimulation` 별도 필드). Agent는 사용자가 명시적으로 요청한 경우에만
`simulate_educational_etch` 또는 Mock Fab Run 기반 `simulate_mock_fab_etch`를 호출한다. 교육용 결과는
항상 `SIMULATED`, `NOT_VALIDATED`, `EDUCATIONAL_ASSUMPTION`으로 표시하며 원인 후보의
지지 근거나 OCAP 합격·불합격 판정에 사용하지 않는다.

### Level 1 — 시간별 깊이 적분

기존 v2의 명시적 식각률 적분 `D = Σ(R_i Δt_i / 60)`을 유지한다. 실측 구간은
`MEASURED`, Level 2가 만든 구간은 `SIMULATED`로 구분한다. 단일 평균 식각률이나
센서만으로 실측 `R(t)`를 만들지 않는다.

### Level 2 — 공정 조건 기반 상대 식각률

각 센서값 `x`와 해당 설정값 `x_ref`로 `δx=(x-x_ref)/|x_ref|`를 계산하고 다음 교육용
선형식을 적용한다.

`relative_rate = clamp(1 + Σ(βx δx), 0.1, 2.0)`

| 변수 | β | 단위 | 출처 |
|---|---:|---|---|
| Source RF | 0.35 | 상대변화당 | TRACE educational assumption v1 |
| Bias RF | 0.25 | 상대변화당 | TRACE educational assumption v1 |
| Chamber Pressure | -0.15 | 상대변화당 | TRACE educational assumption v1 |
| SF₆ Flow | 0.30 | 상대변화당 | TRACE educational assumption v1 |
| O₂ Flow | -0.10 | 상대변화당 | TRACE educational assumption v1 |
| ESC Temperature | 0.05 | 상대변화당 | TRACE educational assumption v1 |

이 값은 문헌 계수나 장비 DOE 결과가 아니며 실제 계측으로 보정되지 않았다. 변수 간
상호작용, 비선형성, 지연, plasma chemistry를 모델링하지 않는다. clamp는 수치적으로
극단적인 데모 출력을 제한하기 위한 것이며 물리적 관리한계가 아니다.

### Level 3 — ARDE와 단순 2D 제거 영역

`AR = depth / opening_width`, `R_ARDE = R_process / (1 + k_ARDE·AR)`를 구간별로 적용한
후 Level 1 식으로 누적한다. 기본 `k_ARDE=0.10` 역시 TRACE 교육용 가정이며 문헌 유도나
실측 보정값이 아니다. 사용자가 명시한 값은 출처를 `user_input`으로 보존한다.

2D 결과는 개구 폭이 일정한 직사각형 제거 영역 좌표와 시간별 depth/AR frame이다.
ARDE만으로 Bowing, Taper, 측벽각, microloading, CD bias를 계산하거나 정확한 profile을
예측했다고 표시하지 않는다. 이를 확장하려면 SEM/CD/depth 정답, 패턴 정보, Recipe
Step별 조건과 별도 보정·검증 데이터셋이 필요하다.

`simulate_educational_etch` 실행에는 명시적 기준 식각률, 패턴 폭, 두 개 이상의 센서
시점이 필요하다. Mock Fab 센서 시점은 `process_series`로 전달되지만 그 결과는 합성
센서 기반 데모이며 실제 장비 예측이 아니다.
