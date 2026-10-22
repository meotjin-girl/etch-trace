# TRACE v1.0.0 문서

현재 기준은 **샘플 사례 기반 단일 조사 그래프**다. 브라우저는 backend HTTP API만 사용하고 agent는 MCP로 근거를 읽는다. 수치와 문서 근거를 보존한 확인 가설을 엔지니어가 검토한다.

| 문서 | 내용 |
|---|---|
| [../README.md](../README.md) | 실행, 환경, 검증 명령, 이전 구성에서 이동 |
| [v1-contract.md](v1-contract.md) | 서비스 간 통합 계약 |
| [api.md](api.md) | Bearer 인증, 공동 재질문·검토·이력·fetch SSE |
| [../deploy/keycloak/README.md](../deploy/keycloak/README.md) | Keycloak 계정 생성·URL·영속성 |
| [keycloak-validation.md](keycloak-validation.md) | Vue·최신 backend 인증 이식 검증 |
| [agent.md](agent.md) | 실제 그래프, 중단·재개, MCP, 보고서 |
| [physics.md](physics.md) | Physics v1 계산 계약, 데이터 경계, 향후 확장 백로그 |
| [architecture.md](architecture.md) | 단일 v1 구조, 저장 책임, 배포·데이터 |
| [frontend.md](frontend.md) | Vue 화면 구조, 필요 API와 예시, 대화형 계약 제안, 목업 서버 |
| [structure-review.md](structure-review.md) | 전체 경로 지도, 구조 점검 결과와 근거 |
| [v1-validation.md](v1-validation.md) | 통합 검증 기록; 실제 실행 여부·범위 확인 |
| [mock-fab.md](mock-fab.md) | 합성 SECS/GEM 모의 장비, 수집기, 로컬 Prometheus FDC 규칙 |
| [idea_brief.html](idea_brief.html) | 과거 초기 기획 참고 자료; 현재 API 계약 아님 |

```text
compose.yaml                유일한 서비스 구성
frontend/                   Vue 3 + TS 화면(Vite), 목업 API(mock/)
sop-ocap/                   SOP·OCAP 원문(SOP 화면·의미 검색 출처)
backend/main.py, v1_*.py     작업·권한·메시지·검토·이력·SSE·SOP
agent/                      유일한 LangGraph, 체크포인트, MCP 어댑터
mcp/                        business/rag/physics 서버와 결정론적 계산
db/                         샘플 사례·문서·적재
agent/tests/                추출·재질문·보고서·검토·재시작
backend/tests/              HTTP 권한·상태·스냅샷·이벤트·경쟁
tests/test_evidence.py       샘플·계산·MCP 경계
tests/test_physics.py        물리 관계식·부족 데이터·유효성 검증
tests/test_sop_*.py          SOP 파서·색인·검색 실험
frontend/tests/              API 계약·스토어·렌더·목업
deploy/nginx.conf           빌드된 화면과 /api(backend) 프록시
fab/                        합성 SECS/GEM 모의 장비·수집기(AWS 배포, 별도 compose)
backend/prometheus/         로컬 Prometheus 설정·FDC 규칙·규칙 테스트
```

구형 `docker-compose*.yml`은 `compose.yaml` include wrapper이며 별도 DB/agent 구성을 시작하지 않는다. 이전 CLI·JSON 요청 예제·CLI 테스트는 서비스 커버리지 확인 후 제거했다. 이전 localStorage 기록은 **로컬 읽기 전용**이며 서버 승인 이력으로 자동 전환하지 않는다.

샘플 데이터는 PHM이 아니다. 문서 조회는 정확한 문서 ID 조회와 `sop-ocap/` SOP·OCAP 의미 검색 두 가지다. Keycloak 로그인 사용자는 공동 작업하며 세부 역할·소유자별 인가는 후속 범위다. 분류별 서브그래프와 담당자 자동 배정을 현재 구현으로 읽지 않는다.

문서 정리는 서비스 테스트 통과를 의미하지 않는다. 내부 신원·명령 ID 경계는 [API 문서](api.md#내부-http-경계), 검증 실행 조건은 루트 README를 참고한다.
