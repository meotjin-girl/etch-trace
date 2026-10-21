# 개발용 Keycloak 로그인

`compose.yaml`의 Keycloak 26.8.1과 Vue `keycloak-js` 26.2.4를 사용한다.
브라우저 Authorization Code + PKCE(S256), 메모리 토큰,
backend JWT 검증 구조다. 자체 비밀번호 입력·회원가입·서버 토큰 저장은 없다.

## 실행과 계정 생성

1. 루트 `.env`에 `.env.example`을 참고해 포트·DB 비밀번호·내부 키와
   `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`를 설정한다.
2. `docker compose -f compose.yaml up -d --build`를 실행한다.
3. `.env.example` 기준 `http://localhost:18080`에서 기본 계정 **`test` / `test`**로
   로그인한다. 새 `trace` realm 초기화 때 생성되며 비밀번호 변경·프로필 입력은 필요 없다.
4. 다른 계정이 필요하면 `/auth/admin/`에서 관리자로 로그인하고 realm을
   `master`에서 `trace`로 전환한 뒤 **Users → Add user**로 계정을 만든다.
   사용자 이름·이메일·이름을 입력하고 Credentials에서 비밀번호를 설정한다.
   비밀번호를 바로 사용할 경우 Temporary를 끈다.
5. 관리자 계정과 앱 계정은 별개다.

`test`는 개발·시연용 공용 계정이다. 현재는 로그인한 모든 사용자가 모든 작업을
조회하고 대기 중 답변·승인·수정을 할 수 있다. 역할·소유자별 분리는 후속 범위다.
`WAITING_INPUT`·`WAITING_APPROVAL` 조건과 승인 경쟁 제어는 유지한다.

## URL과 프록시

`WEB_PORT`만 바꾸면 Compose의 Keycloak URL과 앱 origin도 같이 바뀐다.
다른 호스트에서는 아래 두 값을 함께 지정한다. 한 실행에서 localhost와 IP를
섞지 않는다.

```dotenv
WEB_ORIGIN=http://localhost:18080
KEYCLOAK_URL=http://localhost:18080/auth
```

nginx `/auth/`는 Keycloak으로, `/api/`는 backend로 프록시한다.
backend는 공개 `KEYCLOAK_URL/realms/trace`를 issuer로 검증하고,
컨테이너 내부 JWKS URL로 서명 키를 읽는다. client는 `trace-web`,
API audience는 `trace-api`다. 브라우저에 내부 키·client secret을 전달하지 않는다.
호스트에서 backend만 실행한다면 같은 공개 `KEYCLOAK_URL`을 명시한다.

## 영속성과 변경

개발용 `start-dev`·H2 파일 저장소는 `keycloak_data` 볼륨을 사용한다.
bootstrap 관리자 설정은 새 저장소 초기화에만 적용된다.
`trace-realm.json` 역시 없는 realm을 처음 만들 때만 가져온다.
기존 realm의 origin·redirect URI·audience 변경은 관리자 화면에서 반영한다.
import 파일을 바꾸고 재시작하는 것만으로 기존 realm이 갱신되지는 않는다.
기존 볼륨에 `test`가 없으면 관리자 화면에서 같은 이름과 비밀번호로 한 번 추가한다.
볼륨을 지우지 않고 계정·설정을 관리한다.

`v1_pgdata`와 Keycloak 계정 저장소는 분리된다. backend는 과거 목업 기록에
nullable ID 열을 추가하고 예전 역할·표시 이름은 보존한다. 이름이 같다고
과거 기록을 새 계정에 자동 연결하지 않는다.

## 세션 경계

- REST·SSE 모두 Bearer 헤더를 사용한다. 토큰을 URL이나 local/sessionStorage에
  저장하지 않는다. PKCE 콜백의 임시 상태는 어댑터가 관리한다.
- backend는 RS256/JWKS, issuer, audience, 만료, `sub`, Bearer 타입을 검증한다.
  JWKS 장애는 503, 잘못된 토큰은 401이다.
- SSE는 JWT 만료 시 닫힌다. 갱신된 다른 토큰으로 마지막 seq부터 이어받고,
  같은 토큰의 조기 EOF·네트워크 오류는 명시적으로 다시 연결한다.
- 로그아웃은 먼저 화면·진행 요청·조사 상태를 정리하고 Keycloak POST logout을
  실행한다. backend는 stateless JWT 검증이며 토큰 블랙리스트는 없다.
  이미 발급된 access token 자체는 만료 전까지 유효하다.
- Agent와 MCP 내부 호출은 기존 내부 키·command ID 경계를 유지한다.
  저장된 요청자 정보는 로그인 토큰이나 만료 정보를 대체하지 않는다.

이 구성은 로컬 개발용이다. 운영용 Keycloak DB·TLS·프록시 신뢰 정책은 별도 구성이다.
인증 통합 검증 기록은 `docs/development/v1-validation.md`를 참고한다.
