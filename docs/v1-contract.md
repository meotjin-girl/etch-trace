# v1.0.0 integration contract

## Ownership

- The browser calls only the public backend.
- The backend owns tasks, messages, review decisions, approved snapshots and events.
- The agent owns the sole LangGraph workflow and PostgreSQL checkpoints.
- Business MCP reads sample cases through the backend internal API.
- RAG MCP reads explicitly labelled sample document records.
- Numeric calculations execute in deterministic code, not model prose.
- Keycloak owns login sessions; the backend validates access JWTs. Authenticated
  users collaborate equally, including similar approved-history references.

## Public requests

Public data requests carry `Authorization: Bearer <access token>`, including
fetch SSE. The backend verifies RS256/JWKS, issuer, audience, expiry, subject and
the Bearer token type. Mock identity headers and URL tokens do not authenticate.
All authenticated users can read, answer and review shared work. New actors use
role `user`; historical role labels remain readable without granting privileges.
`GET /api/auth/config` is anonymous and returns only public adapter configuration.

| Method | Path | Body / result |
|---|---|---|
| POST | `/api/ai/tasks` | `{question}` -> 202 `{taskId}` |
| GET | `/api/ai/tasks` | Visible task list, including unfinished tasks |
| GET | `/api/ai/tasks/{id}` | Snapshot, report, messages, reviews and events |
| POST | `/api/ai/tasks/{id}/messages` | `{text}`; authenticated, WAITING_INPUT only |
| POST | `/api/ai/tasks/{id}/approval` | `{action,comment,event_time?,lot_id?}`; authenticated, WAITING_APPROVAL only |
| GET | `/api/ai/tasks/{id}/events` | Events after `after` sequence |
| GET | `/api/ai/tasks/{id}/stream` | Bearer fetch SSE; query after only |
| GET | `/api/ai/investigations` | Saved approved investigations visible to the caller |
| GET | `/api/ai/investigations/{id}` | One saved investigation; 404 when not saved or not visible |
| GET | `/api/sops` | SOP/OCAP summaries from `sop-ocap/` (no markdown) |
| GET | `/api/sops/{id}` | One SOP/OCAP with its original markdown; 404 when missing |

Approval action is `approve` or `revise`. The backend derives the reviewer
from verified claims, never an arbitrary reviewer field in the body. Tasks,
messages and reviews preserve `user_id=sub`; snapshots preserve `approved_by_id`.
Historical mock records retain null account IDs, never inferred by display name.

## States and events

States: `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_APPROVAL`,
`DONE`, `INCOMPLETE`, `FAILED`.

Progress events: `SEARCH_STARTED`, `ANALYSIS_STARTED`, `REPORT_STARTED`.
`QUESTION` carries `{text,missing}` and suspends for collaborator input.
`APPROVAL_REQUIRED` carries `{report}` and suspends for collaborator review.
`DONE`, `INCOMPLETE` and `FAILED` are terminal.
Event sequence IDs support replay and duplicate suppression in the browser.
SSE closes when its verified JWT expires. The browser renews through Keycloak and
reconnects with a different token and its last sequence. Early EOF with the same
token, network failure and malformed saved events require explicit retry.

The report contains `context`, `scored`, `metrics`, `causeCases`, `docIds`,
`documents` (array of `{id,title,text}` with optional `is_demo`, `source`,
`revision`, `notice`, and `distance`), `history` (up to three similar,
approved records visible to the original requester), `checks` (up to three ordered
SOP clauses actually returned by RAG MCP, each `{title,rationale,source:"rag_mcp",docId}`),
`physicsResults` (versioned deterministic calculations with inputs, sources,
assumptions, missing fields and warnings), `stages` (the six specialist-agent
results, each with `key`, `title`, `status`,
`agent_mode`, `findings`, `unknowns`, `caseIds`, `docIds`, and `historyIds`), `summary`,
`unknowns`, `feedback` and `demo:true`. `agent_mode` is `llm` or `rule_based`.
Metrics retain their units and supporting case IDs.
Approval records a reviewed hypothesis, not a confirmed physical root cause.

## Internal service requests

All backend/agent internal requests require `X-Internal-Key`.

- Backend -> agent: `POST /internal/tasks/{id}/run`, initial `{role,content}`
  (`user`: the typed question; `system`: Prometheus alert bundle text, see
  `docs/agent-request.md`) or `{resume:{text}}` or `{resume:{action,comment,by}}`. The backend also sends
  `X-Requester-Name` (URL-encoded) and `X-Requester-Role`, derived from the
  stored task owner, for history attribution. Stored `Requester` values are not
  live login sessions and carry no access token or reconstructed token expiry.
- Agent -> backend: `POST /internal/tasks/{id}/events`,
  `{event_id,type,payload}`; stable event IDs make callback replay idempotent.
- Business MCP -> backend: `GET /internal/cases`.
- Business MCP tools: `search_cases(context)`,
  `analyze_metrics(cases,metrics)`,
  `save_investigation(task_id,command_id,event_id,payload)`.
- Agent completion -> Business MCP -> backend:
  `POST /internal/tasks/{id}/investigation`, a DONE callback with
  `X-Command-ID`. The backend requires a recorded approval and the exact
  reviewed report before atomically saving history and completion. Stable
  command/event IDs suppress duplicate saves.
- RAG MCP tools: `search_documents(document_ids)` resolves exact IDs from
  `etch_documents`; `search_sop(query)` embeds the query against a separate
  pgvector corpus, retrieves 20 candidates, reranks them and returns three
  source clauses. The RAG service needs `OPENAI_API_KEY`; its first semantic
  search indexes the mounted SOP/OCAP source files (`sop-ocap/`) into the persistent
  `sop-postgres` volume. Failed or unavailable semantic search is reported as
  unavailable, not replaced with a locally generated checklist.
- Physics MCP tool: `evaluate_etch_physics(inputs)` evaluates constant-rate etch
  depth, average etch rate and selectivity. It returns calculated, needs-more-data
  or invalid-input results and never invents missing measurements.
- Scope agent -> Business MCP: `list_investigations(user_name,user_role)`;
  the backend authenticates the internal key and returns shared approved history.
  Similar approved reports are references, not proof of the current root cause.

The task ID is the checkpoint thread ID. Waiting states survive restarts.
Interrupted running work must become visibly failed rather than remain running
forever. Approval claims are conditional so competing reviewers cannot both
resume the same waiting state.

## Saved history panel

`GET /api/ai/investigations` and `GET /api/ai/investigations/{id}` are served
by the backend directly from `v1_investigations` (nginx proxies all `/api` to
the backend). Business MCP exposes no browser HTTP routes; its
`list_investigations` / `get_investigation` tools remain for the agent and call
the backend `/internal/investigations` APIs with the internal key. Only saved
approved records are listed; authenticated users share read access.
Active task APIs and read-only local legacy records retain their existing flow.

History uses the existing `v1_investigations.report` snapshot and approval/LOT/time
metadata. It does not copy conversations into saved investigations or return
messages, events, or review timelines. Workflow persistence is unchanged.
