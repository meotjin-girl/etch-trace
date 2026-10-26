# TRACE MCP servers

Four FastMCP servers used only by the Agent Server: Business (`business.py`),
RAG (`rag.py`), Physics (`physics.py`) and Sensor (`sensor.py`).

| Server | Tools |
|---|---|
| Business | `search_cases`, `analyze_metrics`, `list_investigations`, `get_investigation`, `upsert_live_investigation`, `get_live_investigation`, legacy `save_investigation` |
| RAG | `search_documents` (exact IDs), `search_sop` (pgvector top 20 → LLM rerank to 3) |
| Physics | `evaluate_etch_physics`, `compare_reference_runs`, `integrate_etch_rate_series`, `compare_metrology_to_spec`, `analyze_etch_quantitatively`, `simulate_educational_etch` |
| Sensor | `analyze_sensor_timeseries`, `analyze_current_etch_run` (Mock Fab collector `/api/runs`) |

The agent binds read tools to the model; `upsert_live_investigation` is called
only by its `publish` node. Tool contracts beyond this file: [Physics](../docs/physics.md),
[Agent Server](../docs/agent-server.md).

Standalone SOP embedding/retrieval trial: [SOP_EXPERIMENT.md](SOP_EXPERIMENT.md).

All seeded cases and documents are synthetic frontend demo evidence, not
production process records. Original IDs, values, document sections and text
are preserved. `is_demo: true` and `source: "frontend_demo"` travel with evidence;
case `metric_units` and metric result `unit` preserve sec, nm/min, W and mTorr.

## Seed

From the repository root:

```sh
DATABASE_URL=postgresql://user:password@localhost/etch uv run db/seed.py db/schema.sql
```

The schema and both JSON files are applied in one transaction. Re-running
upserts by ID; it does not delete unrelated records. An omitted schema argument
defaults to `db/schema.sql`, regardless of the working directory.

## Run

```sh
cd mcp
uv sync
BACKEND_URL=http://backend:8000 INTERNAL_API_KEY=secret uv run python business.py
DATABASE_URL=postgresql://user:password@postgres/etch MCP_PORT=8001 uv run python rag.py
MCP_PORT=8002 uv run python physics.py
FAB_COLLECTOR_URL=http://localhost:8080 MCP_PORT=8003 uv run python sensor.py
```

All four servers use Streamable HTTP at `/mcp`, default port 8000. Run them in
separate containers or set `MCP_PORT` to avoid port conflicts. Physics and Sensor
should use distinct host ports; the root `.env.example` uses 8004 and 8005.

Physics exposes the v1/v2 deterministic tools plus `simulate_educational_etch`.
That Level 2/3 tool uses declared, uncalibrated assumption coefficients and returns
only `SIMULATED / NOT_VALIDATED` fixed-width profile diagrams. It does not predict
bowing, taper, equipment faults, recipe actions, or lot disposition.

```sh
docker build -t etch-mcp -f mcp/Dockerfile mcp
docker run --rm -p 8000:8000 -e BACKEND_URL -e INTERNAL_API_KEY etch-mcp
docker run --rm -p 8001:8000 -e DATABASE_URL etch-mcp uv run python rag.py
docker run --rm -p 8002:8000 etch-mcp uv run python physics.py
```

Business has no database adapter. Its only case read is:

```http
GET {BACKEND_URL}/internal/cases
X-Internal-Key: {INTERNAL_API_KEY}
Accept: application/json
```

The backend must return a JSON array of frontend-shaped cases (not a wrapper).
It must enforce the internal key. The backend endpoint itself is outside this
unit. HTTP/authentication/JSON errors propagate as tool errors, not empty matches.
RAG reads `etch_documents` directly with parameterized SQL.

## Tool arguments and return values

MCP `tools/call` payloads (the JSON below is the request's `params` object):

```json
{"name":"search_cases","arguments":{"context":{"equipment":"ETCH-07","chamber":"CH-B","recipe":"OX-120","symptom":"endpoint 지연","metrics":{"endpoint_sec":118}}}}
```

Returns an array of original case objects with `score` added. On the MCP wire,
arrays are available as `structuredContent.result`; FastMCP also emits text
content. Uses frontend
weights .30/.20/.25 for equipment/chamber/recipe, symptom substring hits capped
at .20, and .05 for any shared metric. Filters scores below .25, sorts descending
with stable ties, and returns at most five. Context is already extracted;
no question parsing occurs here.

```json
{"name":"analyze_metrics","arguments":{"cases":[{"id":"ETCH-2025-014","equipment":"ETCH-07","chamber":"CH-B","recipe":"OX-120","symptom":"etch rate 저하 endpoint 지연","metrics":{"etch_rate_nm_min":512,"endpoint_sec":94,"rf_reflected_w":18,"pressure_mtorr":42},"cause":"상부 전극 폴리머 누적","action":"챔버 wet clean 및 seasoning","docs":["SOP-ETCH-12#4.2","WI-PM-07#3.1"],"is_demo":true,"source":"frontend_demo"}],"metrics":{"endpoint_sec":118}}}
```

Returns:

```json
[{"key":"endpoint_sec","value":118,"mean":94,"std":0,"deltaPct":25.53191489361702,"z":null,"severity":"비정상","supporting_case_ids":["ETCH-2025-014"],"unit":"sec"}]
```

Population standard deviation, unrounded numeric values and Korean severity
codes match the frontend. Empty observations are omitted; zero mean yields
`deltaPct: 0`; zero standard deviation yields `z: null`. Only finite observations
contribute, and only their case IDs appear in `supporting_case_ids`.

```json
{"name":"search_documents","arguments":{"document_ids":["SOP-ETCH-12#4.2","WI-PM-07#3.1"]}}
```

Returns an array of `{id,title,text,is_demo,source}` from `etch_documents`.
Duplicate IDs are collapsed in first-request order and unknown IDs are omitted.
The first three fields are required; demo metadata is retained when present.

## Tests

```sh
uv run --project mcp python -m unittest discover -s tests -p test_evidence.py -v
EVIDENCE_TEST_DATABASE_URL=postgresql:///isolated_test_db \
  uv run --project mcp python -m unittest discover -s tests -p test_evidence.py -v
```

The database tests require an explicitly supplied disposable database: they
seed twice there. Without that variable, they are skipped.
The remaining tests exercise real MCP dispatch, backend HTTP authentication,
frontend numeric parity, case/document links and missing-data behavior.

## Live investigation storage

`upsert_live_investigation(thread_id, payload)` forwards the full candidate
replacement to `PUT /internal/investigations/live/{thread_id}` with the internal
key; `payload.base_revision` must match the stored revision (409 otherwise).
`get_live_investigation(thread_id)` reads the current candidates, revision and
approval back through `GET /internal/investigations/live/{thread_id}`.

## Legacy approved investigation storage

`save_investigation(task_id, command_id, event_id, payload)` is kept for the
legacy `/api/ai/*` task path. It forwards a DONE
callback to `POST /internal/tasks/{task_id}/investigation` with the internal key
and command ID. The agent calls it after approval. Payload is the original DONE
payload, including the reviewed report. Replays must preserve both IDs.
The backend checks the current command, recorded approval and exact report,
then saves the reviewed snapshot and DONE event in one transaction. Reviewer,
lot and event time come from the backend review. Duplicate requests do not
create another investigation. HTTP/auth/validation failures propagate as tool
errors. MCP has no investigation database write access.

## Approved history reads

Business MCP exposes no browser HTTP routes. The backend serves
`GET /api/ai/investigations(/{id})` directly. The agent's `list_investigations`
and `get_investigation` tools call the backend `/internal/investigations`
endpoints with the internal key; all saved approved records are shared.
