# TRACE v1.0.0 문서

현재 기준은 **샘플 사례 기반 단일 조사 그래프**다. 브라우저는 backend HTTP API만 사용하고 agent는 MCP로 근거를 읽는다. 수치와 문서 근거를 보존한 확인 가설을 엔지니어가 검토한다.

| 문서 | 내용 |
|---|---|
| [../README.md](../README.md) | 실행, 환경, 검증 명령, 이전 구성에서 이동 |
| [v1-contract.md](v1-contract.md) | 서비스 간 통합 계약 |
| [api.md](api.md) | Keycloak Bearer 인증, 공동 재질문·검토·이력·SSE |
| [../deploy/keycloak/README.md](../deploy/keycloak/README.md) | 개발용 로그인, 관리자 계정 생성, realm·client·볼륨 |
| [keycloak-validation.md](keycloak-validation.md) | Keycloak 로그인·공동 작업 구현 검증과 한계 |
| [agent.md](agent.md) | 실제 그래프, 중단·재개, MCP, 보고서 |
| [architecture.md](architecture.md) | 단일 v1 구조, 저장 책임, 배포·데이터 |
| [v1-validation.md](v1-validation.md) | 통합 검증 기록; 실제 실행 여부·범위 확인 |
| [idea_brief.html](idea_brief.html) | 과거 초기 기획 참고 자료; 현재 API 계약 아님 |

```text
compose.yaml                유일한 서비스 구성
frontend/                   backend 연동 화면
backend/main.py, v1_*.py     작업·권한·메시지·검토·이력·SSE
agent/                      유일한 LangGraph, 체크포인트, MCP 어댑터
mcp/                        business/rag 서버와 결정론적 계산
db/                         샘플 사례·문서·적재
agent/tests/                추출·재질문·보고서·검토·재시작
backend/tests/              HTTP 권한·상태·스냅샷·이벤트·경쟁
tests/test_evidence.py       샘플·계산·MCP 경계
deploy/nginx.conf           정적 화면과 /api 프록시
```

구형 `docker-compose*.yml`은 `compose.yaml` include wrapper이며 별도 DB/agent 구성을 시작하지 않는다. 이전 CLI·JSON 요청 예제·CLI 테스트는 서비스 커버리지 확인 후 제거했다. 이전 localStorage 기록은 **로컬 읽기 전용**이며 서버 승인 이력으로 자동 전환하지 않는다.

샘플 데이터는 PHM이 아니다. 현재 문서 조회는 정확한 문서 ID 기반이다. 세분화된 인가와 승인된 조사 이력을 다음 조사의 근거로 검색하는 기능은 미래 범위다. 분류별 서브그래프와 담당자 자동 배정을 현재 구현으로 읽지 않는다.

문서 정리는 서비스 테스트 통과를 의미하지 않는다. 내부 신원·명령 ID 경계는 [API 문서](api.md#내부-http-경계), 검증 실행 조건은 루트 README를 참고한다.
