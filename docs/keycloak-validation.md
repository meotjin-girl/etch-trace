# Keycloak login validation

Date: 2026-10-20. Branch: `feature/keycloak-login`, based on `origin/develop`.

## Implemented scope

- Compose development Keycloak 26.8.1, realm `trace`, public client `trace-web`.
- Administrator-created accounts; no self-registration or password grant.
- Browser keycloak-js 26.2.4, Authorization Code + PKCE S256, memory-only tokens.
- FastAPI RS256/JWKS verification of issuer, audience, expiry, subject and token type.
- Authenticated REST and fetch SSE; mock headers and query identities no longer authenticate.
- All authenticated users share task reads, clarification and review. Workflow state
  checks and competing-review serialization remain.
- Stable `sub` audit fields, separate from display-name snapshots. Historical
  identities remain null rather than being linked by name.
- Internal service authentication remains a separate shared-key boundary.

## Automated checks

- Backend: 61 tests passed against isolated PostgreSQL schemas and an actual
  HTTP JWKS fixture. Coverage includes altered signatures, unsupported algorithms,
  wrong issuer/audience, missing/expired claims, unknown keys, key-service outage,
  spoofed headers, shared access, audit IDs and review races.
- The short test HMAC key initially emitted a warning; it was corrected and the
  four affected security cases passed again without that warning.
- Frontend: 28 Node tests passed, including refresh failure, session invalidation,
  request cancellation, shared review gates, SSE UTF-8/chunk/CRLF parsing,
  cursor resume, explicit retry and duplicate-login prevention during navigation.
- Backend basedpyright: 0 errors and 0 warnings. Ruff, lock consistency, Compose
  validation and Git whitespace checks passed.
- Editor LSPs did not resolve the service-specific Python environment; the actual
  backend environment was used for the type check. JavaScript/JSON editor language
  servers were unavailable; executable tests, build and runtime checks were used.

## Actual service and browser checks

The isolated `trace-keycloak-qa` Compose project used port 18180. Existing stacks
on 18080 and 8080 were not restarted. No OpenAI calls or LangSmith tracing were
needed for this validation.

- All services built and started successfully, including Keycloak readiness.
- Two temporary application accounts were created through the Keycloak admin API.
- The actual login form completed PKCE login and returned to the application.
- A UI question received a real Agent/MCP report over authenticated SSE.
- A different logged-in user opened the shared task and approved it through the UI.
- A deliberate web rebuild disconnected an open stream; explicit reconnect
  restored the persisted DONE event and cleared the connection error.
- Logout locked and cleared the workspace, and the previous refresh token was rejected.
- Blocking the public auth-config request showed the Korean error state; retry
  recovered after the block was removed.
- No token-named localStorage entry or editable mock identity control was present.
- `tests/check_stack.py`, using tokens from two actual PKCE logins, exited 0:
  shared clarification, real MCP evidence, revision, approval, stable reviewer ID,
  replay, invalid-state rejection and incomplete investigation.

The first live login exposed a missing `basic` client scope: modern Keycloak
adds access-token `sub` through its subject mapper. The source realm was fixed,
the QA realm updated, and a separate fresh import of the final source confirmed
`basic`, PKCE S256, disabled registration and disabled password grants.

## Visual evidence

Local ignored evidence: `.omo/qa/keycloak/capture-manifest.json`.
It lists 26 final-build captures: authenticated, anonymous, configuration error
and the upstream Keycloak login page, each at 390 mobile, 1440 and 1920 desktop
widths in light and dark system preferences, plus focused and pressed login
button captures. Authentication controls reserve a 44px row and provide 44px
targets, hover/pressed feedback and an announced, disabled navigation state.
No document horizontal overflow
was observed. The existing application's light-only design and compact typography
were preserved; this work is not a redesign.

Two fresh independent read-only reviews of the final source and all 26 captures
returned PASS with no blocking product or evidence findings. The initial review's
loading-height, button feedback and unnamed login findings were corrected before
those final reviews. Focus and pressed states were captured; full screen-reader
traversal, physical-device safe areas, 200% zoom and measured contrast certification
were not performed. Temporary QA users and owned browser profiles were removed.

## Boundaries

### Existing local endpoint correction

After the initial QA handoff, the user reported that login was missing on their
existing `http://localhost:18080/` tab. That `etchtrace-v1` stack had not been
upgraded: fresh probes returned HTTP 500 at `/` and 404 at `/api/auth/config`,
while the separate 18180 QA stack was healthy.

The existing stack was updated with its original Compose project name:

```bash
WEB_PORT=18080 KEYCLOAK_URL=http://localhost:18080/auth \
WEB_ORIGIN=http://localhost:18080 \
docker compose -p etchtrace-v1 -f compose.yaml \
  up -d --no-deps --build --wait --wait-timeout 240 keycloak backend web
```

The existing PostgreSQL volume was retained; no volumes were deleted and the
8080 stack was not changed. The actual 18080 endpoint then returned 200 for
the app and auth config, and 401 for unauthenticated task access. A fresh
browser verified the **Keycloak 로그인** button and its actual Keycloak
username/password page on 18080. The user's existing browser session could
not be attached, so that session's cached page was not independently verified.

This is a local development identity setup, not a production Keycloak deployment.
H2 and realm/user state persist in the dedicated Keycloak volume.
Existing-realm imports do not migrate client settings; follow the runbook when
changing origin, port or realm settings.

Logout does not cancel running investigations. JWT validation is local rather
than per-request introspection, so an already-issued access token can remain
valid until expiry after logout or account disablement. Role/owner authorization,
production deployment, self-registration and immediate access-token revocation
are outside this sprint.
