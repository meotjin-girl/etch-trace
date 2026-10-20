# TRACE agent 1.0.0

The backend invokes this internal-only service and owns task status, public
messages, failure handling and approved snapshots. This service reads business
evidence only through MCP. PostgreSQL is used only for LangGraph checkpoints.

## Run

From the repository root:

```sh
cd agent
uv sync
export DATABASE_URL='postgresql://trace:trace@localhost:5432/trace'
export INTERNAL_API_KEY='local-development-key'
export BACKEND_URL='http://localhost:8000'
export BUSINESS_MCP_URL='http://localhost:8002/mcp'
export RAG_MCP_URL='http://localhost:8003/mcp'
uv run uvicorn agent.main:app --app-dir .. --port 8001 --workers 1
```

The root `compose.yaml` builds `agent/Dockerfile` with `agent/` as its context.
Its image listens on port 8000. Keep **one worker and one replica**: a per-task
lock serializes the complete checkpoint-read/validate/invoke transaction.
PostgresSaver opens, sets up its tables, and closes in FastAPI lifespan.
Importing modules does not open any database connection.

## Internal contract

`POST /internal/tasks/{uuid}/run` requires `X-Internal-Key: INTERNAL_API_KEY`
and `X-Command-ID: <UUID>` supplied by the backend dispatcher.
The task UUID, canonicalized as a string, is the checkpoint `thread_id`.
The request stays open until the graph interrupts or ends.

Exactly one command is accepted:

```json
{"question":"ETCH-07 CH-B OX-120 endpoint 지연 94초"}
```

```json
{"resume":{"text":"ETCH-07 CH-B"}}
```

```json
{"resume":{"action":"revise","comment":"RF 확인 요청","by":"engineer"}}
```

```json
{"resume":{"action":"approve","comment":"","by":"engineer"}}
```

Returns `{"status":"interrupted","waiting":"clarification"}` or
`{"status":"interrupted","waiting":"review"}`, otherwise
`{"status":"completed"}`. Wrong keys return 403, malformed commands 422,
and duplicate initial commands or resumes for the wrong state 409.
Internal execution/callback errors propagate as HTTP 500; the backend must mark
the task failed. A failed command is not reported as successful or silently retried.

Callbacks go to `BACKEND_URL/internal/tasks/{uuid}/events` with the same key
and the invocation's `X-Command-ID` (read from graph config, never shared globals):
`{event_id,type,payload}`. Types and payloads:

| Type | Payload |
| --- | --- |
| SEARCH_STARTED / ANALYSIS_STARTED / REPORT_STARTED | `{}` |
| QUESTION | `{text,missing}` |
| APPROVAL_REQUIRED | `{report}` |
| DONE | `{report,approved:true,by}` |
| INCOMPLETE | `{reason}` |

`FAILED` is handled by the backend when this HTTP request fails.
Callback IDs are deterministic UUID5 values scoped to the task, event type,
command UUID, clarification number and report revision.
Replaying a failed event within the same command keeps its ID;
each revised report receives a new approval event. Callback nodes and interrupt
nodes are separate, so resuming an interrupt does not repeat a prior callback.

## Evidence and reporting

The parser merges equipment/chamber/recipe/symptom/metrics. It requires any one
scope field plus a recognized symptom. Up to three clarification answers are
accepted; missing context after the third ends INCOMPLETE. Empty case results
also end INCOMPLETE, without review.

MCP URLs accept a service base or an explicit `/mcp` endpoint:

- Business `search_cases(context: dict)` returns the frontend's scored case array.
- Business `analyze_metrics(cases: list, metrics: dict)` returns its metric array.
- RAG `search_documents(document_ids: list[str])` returns `{id,title,text}` arrays.

The adapter uses the real FastMCP `CallToolResult.data` deserialized array.
Reports preserve scored evidence, metric values and extra unit/case-ID fields.
They contain `context`, `scored`, `metrics`, `causeCases`, `docIds`, `documents`
(an array), `summary`, `unknowns`, `feedback`, and `demo:true`.
`causeCases` are the first three non-normal cases in scored order. Only their
deduplicated document IDs are requested. Missing documents are noted in unknowns.

The no-key path is deterministic. Model prose is opt-in only when both
`OPENAI_API_KEY` and `OPENAI_MODEL` are set: the model can select an uncertainty
sentence from an explicit schema enum, not generate metrics or facts.
Model errors fall back to the template. Evidence never goes through model
calculation. Revisions preserve evidence, append visible feedback, regenerate
the report and pause again. The template explicitly states that requested edits
were recorded, not pretended to be automatically implemented.

## Checks

For LangSmith setup, personal tracing projects, fixed datasets, and baseline vs
candidate comparisons, see [the team experiment guide](../docs/agent-experiments.md).
Compose forwards the root `.env` LangSmith settings to this service. Tracing is
disabled by default; enabling it sends graph inputs and outputs to LangSmith.

```sh
cd agent
uv run basedpyright
uv run ruff check .
uv run pytest -q
AGENT_TEST_DATABASE_URL='postgresql://<user>:<password>@localhost/<test-database>' uv run pytest -q
```

The last command enables a real PostgreSQL restart test: four independent Python
processes traverse clarification, review, revision and approval using the same
task UUID. It creates and removes an isolated checkpoint-only test schema.
Without that variable only this integration test is skipped. Other tests use
InMemorySaver, a simple evidence provider and real LangGraph interrupts, plus
FastAPI HTTP and real in-process FastMCP tool dispatch.
