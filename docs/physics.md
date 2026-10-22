# TRACE Physics v1

Physics v1은 TCAD에서 영감을 받은 **0차 물리 관계식 검증 계층**이다. RAG나
엔지니어 판단을 대체하지 않는다. 사용자가 명시한 계측값만 사용해 계산값,
입력값, 단위, 출처, 가정과 부족 데이터를 보고서에 보존한다.

## 구현 범위

| 모델 | 관계식 | 필수 입력 | 결과 |
|---|---|---|---|
| 일정 속도 식각 깊이 | `D = R × t` | `etch_rate_nm_min`, `etch_time_sec` | `expected_etch_depth_nm` |
| 평균 식각 속도 | `R = (D0 - D1) / t` | `pre_thickness_nm`, `post_thickness_nm`, `etch_time_sec` | `average_etch_rate_nm_min` |
| 선택비 | `S = R_target / R_mask` | `target_etch_rate_nm_min`, `mask_etch_rate_nm_min` | `selectivity_ratio` |

`mcp/physics_models.py`가 순수 계산과 검증을 소유하고 `mcp/physics.py`가
`evaluate_etch_physics` MCP 도구를 공개한다. Agent의 `physics_agent`는 모든 모델을
한 번 평가하고 `calculated`, `needs_more_data`, `invalid_input`을 구분한다. 계산 불가는
기존 사례·문서 조사를 중단시키지 않는다.

`endpoint_sec`는 전체 식각 시간이 아니므로 `etch_time_sec`로 재사용하지 않는다.
계산 예상 깊이는 실측 깊이로 표시하지 않는다. 계산 결과만으로 고장 원인 확정,
Recipe 변경 또는 Lot hold/release를 수행하지 않는다.

## 데이터 경계

현재 질문 파서는 명시적인 `nm`, `nm/min`, 초·분 단위가 있는 물리 입력만 추출한다.
모든 입력 출처는 현재 `user_input`이며, 향후 설비 로그 연결 시 `equipment_log`,
계측 시스템 연결 시 `metrology`처럼 원본 출처를 보존해야 한다.

`fab/`의 합성 장비는 120초 run, `sample_offset_s`, RF·가스·압력·온도 센서를
제공하지만 현재 TRACE 입력과 연결되지 않았다. 또한 전후 막 두께와 실측 식각 속도는
제공하지 않는다. 향후 수집기 연동 시 run 시작·종료 이벤트로 확인한 시간만
`equipment_log` 출처로 사용할 수 있으며 현재 샘플 offset을 임의로 완료 시간으로
간주하지 않는다.

보고서 `physicsResults`는 모델·버전·수식·입력·출처·결과·가정·부족 항목·경고를
승인 스냅샷에 그대로 저장한다. 기존 보고서는 빈 배열 기본값으로 읽는다.

## 향후 확장 백로그

다음은 Physics v1에서 의도적으로 제외한다. 실제 데이터 계약, 검증 기준과 별도
모델 버전을 마련한 뒤 확장한다.

- 플라즈마 sheath 해석과 이온 에너지·각도 분포
- 반응종 수송과 Arrhenius 온도 의존성
- RF matching 회로 모델
- chamber conductance와 pumping 모델
- microloading, ARDE/RIE lag
- 패턴 CD/profile 및 공간 식각 균일도 예측
- 다중 Recipe Step 시간 적분
- 측정·모델 불확실성 전파
- Physics 근거만으로 사례가 없는 조사를 계속하는 그래프 정책
- 같은 조사에서 추가 계측값을 받아 Physics 노드를 재실행하는 상태 전이
- 자동 Recipe 변경과 자동 Lot hold/release

Physics v1은 인과 모델이나 고장 분류기가 아니다. 계산된 일관성 또는 편차는 원인
후보를 지지·반박하는 보조 근거이며 센서, 정비, MES, 계측 원본과 엔지니어 승인이
필요하다.
