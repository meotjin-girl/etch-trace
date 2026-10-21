# Local development identity service

This Compose setup runs the official `quay.io/keycloak/keycloak:26.8.1`
server in `start-dev` mode with file-backed H2. It is explicitly for local
development, not a production deployment. The browser adapter is independently
versioned: the frontend integration uses `keycloak-js` 26.2.4.

## Public and internal contract

- The only published service is web. Keycloak is available through nginx at
  `/auth/`, with the path preserved upstream and the external host, port, and
  scheme forwarded. The management interface on port 9000 is not proxied.
- `KEYCLOAK_URL` defaults to `http://localhost:${WEB_PORT:-8080}/auth`.
  `.env.example` selects `WEB_PORT=18080`; copying it therefore uses port 18080.
- `WEB_ORIGIN` defaults to `http://localhost:${WEB_PORT:-8080}`. For another
  hostname, set both `WEB_ORIGIN` and `KEYCLOAK_URL` to the same external origin;
  omit the trailing slash from each, and include `/auth` only in `KEYCLOAK_URL`.
- The imported realm is `trace`; its public browser client is `trace-web`.
  Authorization code flow requires PKCE S256. Implicit flow, direct password
  grants, service accounts, device flow, and CIBA are disabled.
- Redirect and logout URLs allow paths only under the configured web origin.
  `webOrigins` contains that exact origin, never `*`. The realm JSON uses
  Keycloak environment placeholders, not Compose interpolation.
- The browser client's mapper includes `trace-api` in access-token audiences,
  not ID tokens. No application role distinctions or application users are
  imported. All application users have the same access.
- The default `basic` scope is required: its subject mapper adds `sub` to
  access tokens. Omitting it produces tokens the backend correctly rejects.
- Backend receives `KEYCLOAK_URL`, `KEYCLOAK_REALM=trace`,
  `KEYCLOAK_CLIENT_ID=trace-web`, `KEYCLOAK_AUDIENCE=trace-api`, and
  `KEYCLOAK_JWKS_URL=http://keycloak:8080/auth/realms/trace/protocol/openid-connect/certs`.
  JWT validation must check the public issuer
  `<KEYCLOAK_URL>/realms/trace` and the `trace-api` audience while fetching keys
  through that internal JWKS URL. The public issuer must not be replaced with
  the container hostname.
- Backend owns `GET /api/auth/config`, returning
  `{url, realm, clientId}` from the above environment. `frontend/auth.js`
  handles browser `keycloak-js` PKCE and token refresh; `frontend/api.js`
  attaches bearer headers to REST and fetch-based SSE.

## Administrator-created accounts

Self-registration is disabled. Open `/auth/admin/` and sign into the master
realm using `KEYCLOAK_ADMIN_USERNAME` and `KEYCLOAK_ADMIN_PASSWORD`.
The documented development defaults are `admin` / `trace-dev-admin`.
These are bootstrap administration credentials, not an application account.
The manager selects realm `trace`, opens **Users -> Add user**, enables the
account, fills required profile fields, then uses **Credentials -> Set password**.
Use **Temporary: Off** for a ready-to-use local account, or leave it on to require
a password change at first login. No application passwords belong in tracked files.
The bootstrap administrator is a temporary account; create a permanent
administration account and remove the temporary one if keeping this local
instance for continued use.

## Persistence and startup

`keycloak_data` stores H2 state independently of the unchanged `v1_pgdata`
application database volume. Restarting or rebuilding containers preserves
users and realm settings. Bootstrap credentials apply to initial creation;
changing the environment does not reset an existing administrator password.

Startup import skips a realm that already exists. On first initialization,
changing `WEB_PORT` alone updates both hostname and imported client URLs.
For an existing volume, a port/origin change also requires the manager to
update the `trace-web` root/base URLs, redirect URLs, web origins, and logout
redirect URLs in the admin console. Editing the import JSON does not migrate
an existing realm. Do not delete volumes to apply settings; that loses users,
and `docker compose down -v` would also delete the application database.

The readiness check uses Bash `/dev/tcp` against the internal management
`/health/ready` endpoint, with its relative path explicitly set to `/`.
It needs neither curl nor wget. Keycloak has no dependency on web; backend
and web wait for Keycloak readiness, avoiding a reverse-proxy health cycle.

Web builds `./frontend`, including the frontend worker's Dockerfile and
vendored authentication JavaScript. There is no static source bind mount
that could hide built assets; the nginx configuration remains mounted.
Frontend asset changes consequently require `docker compose up -d --build web`.

## Validation

Validate configuration with `docker compose -f compose.yaml config --quiet`.
Also validate with `.env.example` and a different `WEB_PORT` to check origin
interpolation. Backend tests use real PostgreSQL schemas and an HTTP JWKS
server; frontend tests exercise login state, refresh, cancellation and SSE parsing.
`tests/check_stack.py` accepts `TRACE_URL`, `TRACE_ACCESS_TOKEN` and
`TRACE_REVIEWER_TOKEN` from two distinct PKCE logins and verifies shared
clarification, real MCP evidence, revision, approval, identities and replay.
Keep these tokens only in the process environment, never tracked files or logs.

Logout clears the local workspace and ends the Keycloak session, but does not
cancel running investigations. Backend JWT verification does not perform
introspection on every request: previously issued access tokens may remain valid
until expiry after logout or account disablement. SSE connections close at token
expiry and can reconnect with a refreshed token and the last event cursor.
