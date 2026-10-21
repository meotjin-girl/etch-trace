# v1.0.0 integration contract

## Ownership

- Business requests call only the public backend; OIDC login and refresh call Keycloak.
- The backend owns tasks, messages, review decisions, approved snapshots and events.
- The agent owns the sole LangGraph workflow and PostgreSQL checkpoints.
- Business MCP reads sample cases through the backend internal API.
- RAG MCP reads explicitly labelled sample document records.
- Numeric calculations execute in deterministic code, not model prose.
- Keycloak handles login; approved-investigation retrieval as future evidence is deferred.

## Public requests

Task requests, including SSE, require `Authorization: Bearer <access token>`.
FastAPI validates RS256 signature, issuer, audience, expiry and subject using
Keycloak JWKS. Mock identity headers and query parameters do not authenticate.
All authenticated users share all tasks and may answer, revise or approve.
State constraints still apply. The browser uses keycloak-js code flow with
PKCE S256 and keeps tokens in memory, never in URLs or localStorage.
`GET /api/auth/config` is public and returns `{url,realm,clientId}`.

| Method | Path | Body / result |
|---|---|---|
| POST | `/api/ai/tasks` | `{question}` -> 202 `{taskId}` |
| GET | `/api/ai/tasks` | Visible task list, including unfinished tasks |
| GET | `/api/ai/tasks/{id}` | Snapshot, report, messages, reviews and events |
| POST | `/api/ai/tasks/{id}/messages` | `{text}`; authenticated, WAITING_INPUT only |
| POST | `/api/ai/tasks/{id}/approval` | `{action,comment,event_time?,lot_id?}`; authenticated, WAITING_APPROVAL only |
| GET | `/api/ai/tasks/{id}/events` | Events after `after` sequence |
| GET | `/api/ai/tasks/{id}/stream` | Bearer-authenticated fetch SSE; query after |

Approval action is `approve` or `revise`. The backend derives the reviewer
from request identity, never an arbitrary reviewer field in the body.
Keycloak `sub` is persisted as `user_id` and `approved_by_id`; display names
remain snapshots. Historical rows retain null IDs and are not matched by name.
Legacy role values remain readable (`user` for all new user activity),
but neither grant nor restrict permissions.

## States and events

States: `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_APPROVAL`,
`DONE`, `INCOMPLETE`, `FAILED`.

Progress events: `SEARCH_STARTED`, `ANALYSIS_STARTED`, `REPORT_STARTED`.
`QUESTION` carries `{text,missing}` and suspends for user input.
`APPROVAL_REQUIRED` carries `{report}` and suspends for user review.
`DONE`, `INCOMPLETE` and `FAILED` are terminal.
Event sequence IDs support replay and duplicate suppression in the browser.

The report contains `context`, `scored`, `metrics`, `causeCases`, `docIds`,
`documents` (array of `{id,title,text}`), `summary`, `unknowns`, `feedback`
and `demo:true`. Metrics retain their units and supporting case IDs.
Approval records a reviewed hypothesis, not a confirmed physical root cause.

## Internal service requests

All backend/agent internal requests require `X-Internal-Key`.

- Backend -> agent: `POST /internal/tasks/{id}/run`, initial `{question}`
  or `{resume:{text}}` or `{resume:{action,comment,by}}`.
- Agent -> backend: `POST /internal/tasks/{id}/events`,
  `{event_id,type,payload}`; stable event IDs make callback replay idempotent.
- Business MCP -> backend: `GET /internal/cases`.
- Business MCP tools: `search_cases(context)`,
  `analyze_metrics(cases,metrics)`.
- RAG MCP tool: `search_documents(document_ids)`.

The task ID is the checkpoint thread ID. Waiting states survive restarts.
Interrupted running work must become visibly failed rather than remain running
forever. Approval claims are conditional so competing reviewers cannot both
resume the same waiting state.
