# Backend v1 integration notes

Public routes and simple `/internal/tasks/{id}/run` bodies follow
`docs/development/v1-contract.md`. All internal requests use `X-Internal-Key`.

Each accepted command gets a new UUID, exposed as `command_id` in the task
snapshot and sent to the agent as `X-Command-ID`. The agent MUST echo that
header on every callback for that invocation. This preserves the simple bodies:

```json
{"question":"Investigate etch"}
{"resume":{"text":"CH-A"}}
{"resume":{"action":"approve","comment":"Reviewed","by":"Engineer"}}
```

Callbacks require `X-Internal-Key`, `X-Command-ID`, and this body:

```json
{"event_id":"stable-event-id","type":"APPROVAL_REQUIRED","payload":{"report":{}}}
```

`event_id` is namespaced by the command UUID in backend persistence.
Replay of the same event returns `{"accepted":false,"duplicate":true}`.
A new event for an older command returns 409, even if the task is now RUNNING
again. Conflicting reuse of an event ID also returns 409. New callbacks require
RUNNING; terminal and waiting tasks cannot be reopened by delayed callbacks.

QUESTION requires `payload.text` (or `payload.question`).
APPROVAL_REQUIRED and DONE require `payload.report`; missing report fields are
filled with the documented empty frontend shape. Other payloads are preserved.
Responses to accepted public commands are 202 `{"taskId":"..."}`.
Snapshots contain messages, reviews, events, and an optional investigation.
An investigation saves the exact reviewed report, reviewer identity and optional
event_time/lot_id only when an approved command subsequently reaches DONE.

Defaults: DATABASE_URL=postgresql://trace:trace@localhost:5432/trace,
AGENT_URL=http://agent:8001, INTERNAL_API_KEY=dev-internal-key.

Run `cd backend && uv sync && uv run pytest tests -q`.
Tests use real PostgreSQL, an isolated schema per test and a local HTTP agent
stub. Set TEST_DATABASE_URL if `postgresql:///postgres` is unavailable.
