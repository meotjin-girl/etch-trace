# TRACE Agent Server

Installable, independent `src/trace_agent` application. No imports from `agent/`,
no backend database access, no specialist graphs, and no custom checkpoint saver.
Graph ID `trace`; `investigator` is an alias of the same graph.

## Local run

From the repository root:

```sh
cd agent-new
cp .env.example .env
# Edit .env: real OPENAI_API_KEY, INTERNAL_API_KEY, issuer/JWKS and reachable MCP URLs.
uv sync --locked --group dev
uv run --no-sync langgraph dev --host 127.0.0.1 --port 2024 --no-browser
```

The CLI loads `.env`. Existing `OPENAI_MODEL` is honored; the default when absent
or empty is `gpt-4.1-mini`. Missing `OPENAI_API_KEY` fails a run with
`ConfigurationError`, not a fabricated candidate or successful fallback.
MCP and Keycloak must be independently reachable; this command does not start them.

Local dev state lives in `.langgraph_api/` under the working directory. Keep that
directory across restarts. LangGraph Server supplies the checkpointer.
This is a development deployment, not the production LangGraph platform runtime.

## Docker run

From the repository root, after configuring `agent-new/.env`:

```sh
docker build -t trace-agent-dev ./agent-new
docker volume create trace-agent-dev-state
docker run --rm --name trace-agent-dev \
  --env-file agent-new/.env \
  --mount type=volume,source=trace-agent-dev-state,target=/app/.langgraph_api \
  -p 127.0.0.1:2024:2024 \
  trace-agent-dev
```

The image starts `langgraph dev --host 0.0.0.0 --port 2024 --no-browser --no-reload`.
The state volume is deliberately supplied externally, not created by the image.
Container URLs must resolve from inside the container: use a shared Docker network
and service DNS, or `host.docker.internal` for host services on Docker Desktop.
Keep `KEYCLOAK_ISSUER` equal to the token's public `iss`; set
`KEYCLOAK_JWKS_URL` separately if keys need an internal URL.
Alternatively omit `KEYCLOAK_ISSUER` and supply the existing `KEYCLOAK_URL` plus
`KEYCLOAK_REALM` (default `trace`). The issuer then becomes
`KEYCLOAK_URL/realms/KEYCLOAK_REALM`. A missing `.env` file is allowed when all
settings are injected through the environment. `/ok` is a public health endpoint.
No Compose file is required or modified.

## Authentication and request contract

Send `Authorization: Bearer <Keycloak access token>`. Validation requires RS256,
the configured JWKS and exact issuer, audience `trace-api`, expiration, nonempty
subject, and payload `typ=Bearer`. For Studio on the localhost-only development
server, configure custom headers `X-Auth-Scheme: custom` and `X-Internal-Key` from
the root environment. This explicit trusted credential is independent of Studio's
own LangSmith bearer. Public nginx routes strip both headers and continue to
require a Keycloak access token. LangSmith login alone is not local API access.
All authenticated users collaborate on all threads; there are no owner filters.

An internal emitter may send `X-Internal-Key` only without an Authorization
header. An invalid or empty Authorization header never falls back to the internal
key. The browser proxy must strip `X-Internal-Key`; never ship it to browser code.
The internal identity is `trace-alert-emitter`.

Create a thread, then run it; the server-generated thread UUID is also the
business investigation UUID:

```sh
curl -sS http://localhost:2024/threads \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' -d '{}'

# Set THREAD_ID to the returned thread_id.
curl -N "http://localhost:2024/threads/$THREAD_ID/runs/stream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"assistant_id":"trace","input":{"request":{"role":"system","content":"[경보] ETCH-02 / CH-A / Lot LOT-1 / Wafer W01 / RCP-1\n- 15:15:11 FDC FDC_WATCH pressure z=4.1 (OCAP-ETCH-PRESSURE)"}},"stream_mode":["values"],"multitask_strategy":"reject","on_disconnect":"continue"}'
```

Follow up on the **same** thread with
`{"request":{"role":"user","content":"첫 후보의 조치만 다시 조사해 주세요"}}`.
Standard `{"messages":[{"role":"user","content":"이 계산을 설명해 주세요"}]}`
also works. An alert envelope is appended as a human message, never as a system
instruction, and is consumed once. A second system envelope cannot replace the
immutable alert. The public input schema excludes candidates, revision and approval.
Use one active run per thread (`multitask_strategy=reject`).

## Investigation lifecycle

`prepare -> agent <-> ToolNode -> reason -> publish` retains the original single
ReAct domain behavior. Evidence tools are `search_cases`, `analyze_metrics`,
`search_documents`, `search_sop`, `evaluate_etch_physics`, `list_investigations`.
The last retains the existing MCP `user_name/user_role` argument signature using
shared service attribution; it does not install an ownership filter.

`reason` uses ChatOpenAI's schema-constrained output, not prose parsing. Each
candidate has cause, action, a concise evidence rationale, checks, case IDs,
document IDs, unknowns, and an ID. The model returns null IDs for new candidates;
code assigns UUID4. Existing IDs must be explicitly retained; unknown and duplicate
IDs fail the run. A changed proposal is a full replacement, including unchanged
candidates. Null candidates or an identical list produces no business write.
Summary-only changes do not increment the revision.

The mandatory publication node calls Business MCP
`upsert_live_investigation(thread_id,payload)` with `base_revision=0` initially,
then the matching revision. Thread identity comes from execution configuration,
not model arguments. Publication errors fail the run; no fake successful record is
checkpointed. Initial alert investigations must produce a nonempty candidate list.
General conversations without proposals can stay conversation-only.

Before followups on a published investigation, `get_live_investigation(thread_id)`
refreshes candidates, revision and approval. Approval remains backend-owned and
immutable. Approval never disables conversation or editing; the snapshot is shown
to the model separately from current candidates. There is no `record_selection`.
Unknown identifiers in a user-started investigation remain empty rather than invented.

## Checks

```sh
cd agent-new
uv sync --locked --group dev
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync basedpyright
```

Tests use a real compiled graph and ToolNode, real in-process FastMCP transport,
and only replace model responses and external business storage. Signed JWT tests
exercise cryptographic validation, including invalid tokens and internal-key
precedence. Verification evidence and remaining integration limits are in
`docs/verification.md`.

`typings/` contains narrow declarations for the upstream graph and ChatOpenAI
methods used here. They fill incomplete upstream annotations for the strict
`basedpyright` gate; runtime execution still uses the installed libraries. No
diagnostics are disabled and no runtime compatibility layer is installed.
