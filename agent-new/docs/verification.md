# Standalone agent verification

Verified on October 23, 2026, on macOS arm64. All changes are under `agent-new/`.
No Compose invocation, sibling source modification, or commit was made.

## Environment isolation

Owned temporary root: `/tmp/trace-agent-new.2xedbc`.
Dependencies were installed with:

```sh
cd agent-new
UV_CACHE_DIR="$RUN_TMP/uv-cache" \
UV_PROJECT_ENVIRONMENT="$RUN_TMP/venv" uv sync --group dev
```

The resolved environment used Python 3.13.14 and LangGraph API 0.16.5.
The package supports Python >=3.12. Temporary environments, caches, distribution
artifacts, server state, and owned Docker resources were removed after checking.

## Test and static-analysis evidence

```text
$RUN_TMP/venv/bin/pytest -q -o cache_dir=$RUN_TMP/pytest-cache
35 passed, 1 warning

$RUN_TMP/venv/bin/ruff check .
All checks passed!

$RUN_TMP/venv/bin/basedpyright --pythonpath $RUN_TMP/venv/bin/python
0 errors, 0 warnings, 0 notes
```

The warning is an upstream `AuthlibDeprecationWarning` from FastMCP 2's import
of `authlib.jose`. It is not suppressed. The workspace LSP uses a different
interpreter and reports unresolved dependency imports; the isolated environment's
explicit strict type-check command above is the verification result.

The tests execute the real compiled StateGraph, real ToolNode and real
in-process FastMCP client/server protocol. Scripted model responses replace only
model inference; the external business store is a stateful test service enforcing
revision and identity semantics. Coverage includes:

- Model -> tool -> model loop and mandatory initial publication.
- Rebuilding the graph with the same checkpointer/thread and continuing messages.
- Initial create followed by update of the same business UUID and candidate UUID.
- Null or identical proposals leaving business revision unchanged.
- New UUID4 allocation; malformed, unknown, duplicate and empty replacements fail.
- Approval readback, conversation after approval, and edits preserving the snapshot.
- Publication failure without a successful revision.
- Missing OpenAI key and invalid thread UUID failure paths.
- Legacy alert parser observations, units, missing samples, source preservation.
- Actual RSA-signed JWT validation via a real ephemeral HTTP JWKS server.
- Bad signature, issuer, audience, expiration, subject or token type rejection.
- Internal-key authentication, missing/bad credentials, and no fallback from
  malformed or empty Authorization.
- Existing `KEYCLOAK_URL` plus realm deriving the exact issuer.

## Real development server

Started the actual CLI from the owned temporary directory with no `.env` file:

```sh
INTERNAL_API_KEY=local-verification-only \
KEYCLOAK_URL=http://127.0.0.1:20348/auth \
KEYCLOAK_REALM=trace \
LANGSMITH_TRACING=false \
"$RUN_TMP/venv/bin/langgraph" dev \
  --config "$REPO/agent-new/langgraph.json" \
  --host 127.0.0.1 --port 20347 --no-browser --no-reload
```

Observed:

| Probe | Result |
|---|---|
| Unauthenticated `GET /ok` | 200, `{"ok":true,"services":{}}` |
| Unauthenticated `POST /threads` | 401 |
| Internal-key `POST /threads` | 200, server-generated UUID |
| Invalid Bearer plus valid internal key | 401; no fallback |
| Internal-key `POST /assistants/search` | 200; `trace` and `investigator` |
| `GET /assistants/{assistant_uuid}/schemas` | 200; input keys only `messages`, `request` |
| `POST /threads/{uuid}/runs/stream`, canonical system envelope | Human message and parsed alert checkpointed; explicit SSE error `{"variable":"OPENAI_API_KEY"}` |
| Graceful stop and restart using retained `.langgraph_api` | Same thread, message ID, alert and consumed request restored |
| Followup via `investigator` on that same thread | Second human message appended once; original alert retained; missing-key error remains explicit |

The missing-key run has revision 0 and no fabricated candidates.
The schemas endpoint requires the assistant UUID, not the graph slug.

## Packaging and Docker

`uv build --out-dir "$RUN_TMP/dist"` exited 0 and built:

- `trace_agent-1.0.0.tar.gz`
- `trace_agent-1.0.0-py3-none-any.whl`

`docker build -t trace-agent-new-owned-2xedbc agent-new` exited 0, including
`uv sync --locked --no-dev` in the image.

Started the image with injected environment only, an externally supplied named
volume at `/app/.langgraph_api`, and a random loopback host port (32770).
Inspection confirmed working directory `/app` and the expected volume mount.
The container's unauthenticated `/ok` returned 200, assistant search registered
both graph IDs, and invalid Authorization plus a correct internal key returned
401. No dotenv file was copied or required.

## Decisions and limits

### Integration follow-up

After the isolated checks above, the deployed stack completed paid OpenAI calls,
real Keycloak login, initial publication, same-thread candidate updates, approval,
and post-approval conversation. Aside also opened the actual Studio graph and
completed a Chat run. Studio requires the documented custom connection headers.

The final pre-commit run passed **37 tests**, Ruff, and basedpyright with zero
errors or warnings. Deployment evidence and the known Studio checkpoint-replay
revision limitation are recorded in
[`docs/agent-server-validation.md`](../../docs/agent-server-validation.md) and
[`docs/agent-server.md`](../../docs/agent-server.md).

The single ReAct loop is followed by a separate schema-constrained proposal call,
then a mandatory deterministic publication node. This follows the official
LangGraph structured-response pattern consulted through Context7. Optional
model-selected publication was rejected because it cannot guarantee that initial
proposals reach the backend.

Focused declarations in `typings/` describe only the consumed upstream APIs and
avoid suppressing missing/partial dependency type diagnostics. Runtime graph,
model, SDK, and MCP implementations remain upstream packages.

No successful paid OpenAI invocation or deployed Keycloak realm was exercised in
this isolated verification. Successful generation/publication was verified through
the compiled graph with the narrow model seam and real MCP transport; production
backend persistence and realm integration belong to the integration deployment.
The existing history tool still receives its required `user_name/user_role`
arguments with shared service attribution. New live MCP tool signatures match the
contract exactly.

Self-review: source modules each have one responsibility and at most 164
nonblank/noncomment lines. Inputs and external records cross typed parsing
boundaries; request roles are exhaustively handled. No type ignores, casts, fake
success paths, silent catches, or added logging were introduced. Exception
instances deliberately remain mutable because Python context managers set their
traceback fields. Tests exercise failure paths rather than pinning prompt prose.
