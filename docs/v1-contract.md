# v1.0.0 integration contract

## Ownership

- The browser calls only the public backend.
- The backend owns tasks, messages, review decisions, approved snapshots and events.
- The agent owns the sole LangGraph workflow and PostgreSQL checkpoints.
- Business MCP reads sample cases through the backend internal API.
- RAG MCP reads explicitly labelled sample document records.
- Numeric calculations execute in deterministic code, not model prose.
- Keycloak and approved-investigation retrieval as future evidence are deferred.

## Public requests

Requests carry URL-encoded `X-User-Name` and `X-User-Role`.
Roles are `worker`, `engineer`, `admin`. These are development identities,
not verified authentication. Workers see only their own tasks; engineers and
administrators may read all tasks. Only engineers may approve or revise.

| Method | Path | Body / result |
|---|---|---|
| POST | `/api/ai/tasks` | `{question}` -> 202 `{taskId}` |
| GET | `/api/ai/tasks` | Visible task list, including unfinished tasks |
| GET | `/api/ai/tasks/{id}` | Snapshot, report, messages, reviews and events |
| POST | `/api/ai/tasks/{id}/messages` | `{text}`; owner, WAITING_INPUT only |
| POST | `/api/ai/tasks/{id}/approval` | `{action,comment,event_time?,lot_id?}`; engineer, WAITING_APPROVAL only |
| GET | `/api/ai/tasks/{id}/events` | Events after `after` sequence |
| GET | `/api/ai/tasks/{id}/stream` | SSE; query user_name/user_role/after |

Approval action is `approve` or `revise`. The backend derives the reviewer
from request identity, never an arbitrary reviewer field in the body.

## States and events

States: `QUEUED`, `RUNNING`, `WAITING_INPUT`, `WAITING_APPROVAL`,
`DONE`, `INCOMPLETE`, `FAILED`.

Progress events: `SEARCH_STARTED`, `ANALYSIS_STARTED`, `REPORT_STARTED`.
`QUESTION` carries `{text,missing}` and suspends for owner input.
`APPROVAL_REQUIRED` carries `{report}` and suspends for engineer review.
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
  `analyze_metrics(cases,metrics)`,
  `save_investigation(task_id,command_id,event_id,payload)`.
- Agent completion -> Business MCP -> backend:
  `POST /internal/tasks/{id}/investigation`, a DONE callback with
  `X-Command-ID`. The backend requires an engineer approval and the exact
  reviewed report before atomically saving history and completion. Stable
  command/event IDs suppress duplicate saves.
- RAG MCP tool: `search_documents(document_ids)`.

The task ID is the checkpoint thread ID. Waiting states survive restarts.
Interrupted running work must become visibly failed rather than remain running
forever. Approval claims are conditional so competing reviewers cannot both
resume the same waiting state.

## Saved history panel

`GET /api/ai/investigations` and `GET /api/ai/investigations/{id}` route
through Business MCP `list_investigations` / `get_investigation`, then the
backend `/internal/investigations` APIs. Internal reads require the internal
key and recheck the forwarded identity. Only saved approved records are
listed; worker ownership and engineer/admin read access are preserved.
Active task APIs and read-only local legacy records retain their existing flow.

History uses the existing `v1_investigations.report` snapshot and approval/LOT/time
metadata. It does not copy conversations into saved investigations or return
messages, events, or review timelines. Workflow persistence is unchanged.
