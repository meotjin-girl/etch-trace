# v1.0.0 validation ledger

Executed on 2026-10-20 against `etchtrace-v1`, port 18080. The existing
`etch_trace` POC on port 8080 was not stopped or modified.

## Aside browser checks

- [x] Suggested endpoint question fills composer without submitting.
- [x] Suggested etch-rate and RF questions each fill composer correctly.
- [x] Send button and Enter create a server task; Shift+Enter inserts a newline.
- [x] Missing scope or symptom asks a clarification in the same conversation.
- [x] Clarification answer resumes the original task and preserves metrics.
- [x] Search, analysis and report stages reflect server events.
- [x] Open/close evidence panel and all seven distinct case/document citations work.
- [x] New investigation clears view without cancelling another task's history.
- [x] Investigation navigation restores the investigation view.
- [x] Records navigation lists pending, incomplete, failed and completed work.
- [x] Record selection loads persisted detail and chronological events.
- [x] Opening a waiting task resumes its input or review controls.
- [x] Review dialog opens; close and cancel do not submit a decision.
- [x] Reviewer is read-only and derived from selected mock user.
- [x] Engineer revision displays the requested feedback before re-review.
- [x] Engineer approval persists the snapshot and ASIDE-QA-LOT metadata.
- [x] Worker and administrator approve/revise buttons are disabled.
- [x] Another worker sees an empty list; API tests also deny detail/events/SSE.
- [x] Identity change resets the old task and reloads the allowed records.
- [x] Refresh and retry buttons restore server state without task creation.
- [x] Disabled document-search navigation remains explicitly unavailable.
- [x] A real failed request showed feedback; retry recovered after routing repair.
- [x] Phone navigation, evidence and review controls work in an Aside 390px iframe.

Legacy local records were verified with isolated storage fixtures in the
frontend tests, not by inserting fake records into the user's browser storage.
The user browser's local data was not cleared or rewritten.

## Service checks

- [x] Sample seed is idempotent and retains all five original case IDs.
- [x] Similarity and population-statistic results preserve source case IDs.
- [x] Both MCP servers respond through real Streamable HTTP tool calls.
- [x] Agent checkpoints suspend and resume the same task thread.
- [x] Event replay is ordered; repeated callback IDs do not duplicate events.
- [x] Competing review requests cannot both resume a pending revision.
- [x] Separate-process PostgreSQL tests preserve clarification/review checkpoints.
- [x] Backend startup preserves waiting states and marks interrupted active work FAILED.
- [x] The full stack starts without an external model API key.

## Release evidence

| Check | Command | Observed |
|---|---|---|
| Backend | `cd backend && uv run pytest -q` | 46 passed |
| Agent | `cd agent && uv run pytest -q` | 24 passed, PostgreSQL test skipped without its DSN |
| Agent process restart | `cd agent && AGENT_TEST_DATABASE_URL=postgresql:///postgres uv run pytest -q tests/test_checkpoint.py` | 1 passed, four separate processes |
| Evidence | `EVIDENCE_TEST_DATABASE_URL=postgresql:///etch_evidence_v1_20261020 uv run --project mcp python -m unittest discover -s tests -p test_evidence.py -v` | 16 passed |
| Frontend | `node --test frontend/frontend.test.mjs` | 17 passed |
| Types and lint | backend/agent `uv run basedpyright`, `uv run ruff check .`; MCP `uvx basedpyright --project mcp` | Clean |
| Actual stack | `TRACE_URL=http://localhost:18080 python3 tests/check_stack.py` | PASS |
| Compose | canonical config and both compatibility entry points | Seven services, same volume |

Observed task IDs:

- HTTP full flow: `3eb13494-34fa-4c12-9ea8-c69fa1b55ad1`.
- Final rebuilt deployment flow: `1dfc4908-dd93-4dcc-97ab-c9f44e663367`.
- Aside revised and approved: `8d4253ac-522f-4f60-9952-679e4f154a42`.
- Aside clarification with 118 sec preserved: `83b12a30-338a-410c-819e-725f1ee8e4c2`.

Screenshots live in the local Aside session's `artifacts/v1-qa/` directory:
`desktop-history-final.png`, `mobile-final.png`.
The desktop viewport is 1600x1000 CSS pixels; the mobile iframe is 390x844.
Browser zoom is 90% (devicePixelRatio 1.8), so capture rectangles compensate
for the screenshot transport's 2x scale. Document scrollWidth equals 390 in
the mobile frame; the review dialog stays inside its viewport.

Integration defects found and fixed: command-ID callback header omission,
FastMCP typed-result conversion, sample metadata projection, service startup
readiness, stale nginx container DNS, duplicate clarification rendering,
role-change ownership mismatch, modal citation visibility and narrow citation
grid/status badge wrapping.

Keycloak, semantic/vector search, historical investigations as retrieval
evidence and durable queued command recovery remain follow-up work.
Running work fails visibly after backend restart; there is no automatic retry.
No GitHub issues were posted. External-model narrative mode was not tested.

## 2026-10-21 backend-integration checks

Branch `feature/backend-integration` on develop `d2be127`. Full stack ran with
`docker compose -f compose.yaml -p trace-fe-check up -d --build` (`WEB_PORT=18080`,
separate project name so existing containers were untouched); `OPENAI_API_KEY`
was present, `OPENAI_MODEL` was not (agents ran rule-based).

| Area | Command or path | Result |
|---|---|---|
| Backend | `TEST_DATABASE_URL=… uv run --group dev pytest` (temporary pgvector container) | 52 passed |
| Frontend | `npm run type-check && npm test && npm run build` | 35 passed, build ok |
| SOP parser/index | `SOP_TEST_DATABASE_URL=… uv run --project mcp --group rag-experiment python -m unittest discover -s tests -p 'test_sop_*.py'` | 21 run, 18 passed, 3 known data assertions fail (see structure-review 2.1) |
| API flow | question without scope → QUESTION → `/messages` → APPROVAL_REQUIRED → worker revise 403 → engineer revise → APPROVAL_REQUIRED → approve → DONE | 16 events in order; investigation saved with lot; SSE replay closes on DONE |
| Report content | endpoint 135 s from the question; 5 stages; RAG checks `SOP-ETCH-12#4.2`, `OCAP-ETCH-EPD#4.1`, `#4.2` | ok |
| History | `GET /api/ai/investigations/{id}` served by backend | ok |
| SOP | `GET /api/sops` 22 rows; `/api/sops/OCAP-ETCH-RF` 200; missing 404; no identity 401 | ok |
| Vector DB | `sop_rag_model_chunks` in sop-postgres | 240 chunks, 22 documents, text-embedding-3-small (1536) |
| Browser (headless Chrome, 1440x900) | ask → typed clarification → report (sidebar steps 1–7 done, 8 active) → 미승인 → 승인 → 완료; records list; SOP OCAP detail | no network notice, no script errors |

Not covered: agent LLM narrative mode (`OPENAI_MODEL` unset), TOKEN streaming
(agent does not emit it yet), mobile layouts.
