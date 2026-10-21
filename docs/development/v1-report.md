# v1.0.0 integration report

Date: 2026-10-20

## Delivered

The existing static investigation screen now uses server-owned tasks, evidence,
reports, engineer decisions and complete history. The application remains plain
HTML/CSS/JavaScript; no frontend framework migration was introduced.

```text
browser -> nginx -> backend -> agent -> business-mcp -> backend case API
                                  \-> rag-mcp -> document database
```

- `backend/`: mock identity boundary, owner-scoped reads and clarification,
  engineer review, PostgreSQL event journal and approved snapshots, SSE replay.
- `agent/`: the only LangGraph runtime, deterministic intake/report generation,
  MCP evidence orchestration, PostgreSQL checkpoint interruption and resume.
- `mcp/`: separate read-only business and document services using Streamable HTTP.
- `db/`: the original five frontend cases and five document clauses, clearly
  marked as demo data, with idempotent seed commands.
- `frontend/`: server-driven progress and results, review/revision controls,
  all-status records, identity selection and mobile navigation.
- `compose.yaml`: isolated service network, health-gated startup and nginx.
  The two previous Compose entry points resolve to this same configuration.

The CLI package under `src/etch_investigator`, its examples and CLI-specific
tests were removed after equivalent service behavior was covered. The old
backend graph, PHM tool pipeline and import-time DB entry points were removed
as duplicate runtimes. Existing database PHM tables are not dropped or rewritten.
New business tables use a `v1_` prefix.

## Breaking API changes

The implemented contract is [api.md](api.md); service callback payloads are
documented in [v1-contract.md](v1-contract.md) and
`backend/AGENT_CONTRACT.md`.

1. Task creation requires only `question`, not `tool` or `run_id`.
2. Incomplete input produces `WAITING_INPUT`; the owner answers through
   `/messages` on the same task.
3. Intake requires a symptom plus equipment, chamber or recipe. Current
   measured metrics are optional and survive clarification.
4. Case similarity and population statistics use the original frontend domain,
   units and data. They are not PHM standardized-sensor calculations.
5. Engineer decisions use `approve` or `revise`; reviewer identity is derived
   from the request actor, not the modal's name field.
6. The public task list includes every visible status; task detail includes
   questions, added answers, progress, reports, reviews and approval metadata.
7. SSE visibility matches detail visibility. Cursor replay and callback IDs
   prevent duplicate events and stale-command updates.
8. Approval saves an immutable reviewed snapshot, not a confirmed physical
   root cause. Another engineer can review; assignment is not required.

Legacy browser records are read-only and explicitly labelled. They are never
converted into authoritative server approvals. No user localStorage was cleared
or overwritten during validation.

## Run and test

```sh
cp .env.example .env
docker compose up --build -d --wait
# WEB_PORT defaults to 8080; .env.example uses 18080 to coexist with the POC.
```

The tested deployment is `etchtrace-v1` at `http://localhost:18080`.
The user's existing POC project on port 8080 was left running unchanged.
Only nginx is externally published.

Test outcomes and the complete Aside button checklist are in
[v1-validation.md](v1-validation.md). The combined verified suites contain
104 passing tests: backend 46, Agent 25 including a separately enabled
PostgreSQL process-restart test, evidence/MCP 16, frontend 17. The real
multi-service HTTP scenario also passed.

The Aside tests covered desktop and a 390x844 iframe viewport: suggested
questions, button/keyboard submission, clarification, all case/document
citations, evidence panel, record navigation and resume, approval modal
close/cancel/revise/approve, identity and role changes, empty lists, refresh
and network recovery. Worker and administrator approval restrictions were
checked in the UI and API. Screenshots are in the local Aside session's
`artifacts/v1-qa/` directory.

## Explicit limits and follow-up issue candidates

These are handoff candidates, not posted GitHub issues.

| Candidate | Suggested ownership | Acceptance boundary |
|---|---|---|
| Replace mock headers with Keycloak | Authentication/backend | One verified actor provider shared by JSON requests and SSE; preserve current authorization rules |
| Search past approved investigations as evidence | Backend/MCP/Agent | Return source snapshots, review state and later field-verification outcome; never treat approved hypotheses as confirmed causes |
| Durable dispatch and restart recovery | Backend/Agent | Persist accepted commands and reconcile checkpoints; automatic resume must not repeat approval effects |
| Semantic/vector document retrieval | RAG/MCP | Versioned embeddings and retrieval evaluations; preserve exact citation IDs and source clauses |
| Optional model-generated revision narrative | Agent | Apply reviewer feedback while leaving deterministic metrics and sources unchanged; retain no-key behavior |
| Continuous integration | Team | Run service tests with isolated PostgreSQL and browser workflow on every PR |
| Operational dataset ingestion | Data/backend | Explicit mapping of equipment, recipe, units and case provenance, without mixing PHM normalization into physical values |

v1 deliberately uses impersonable mock identities. It is a demo authorization
boundary, not production authentication. Internal callbacks require the shared
service key and active command ID.

Without a language model, the report is deterministic. Revision feedback is
retained visibly; automatic semantic rewriting is not claimed. Document
retrieval resolves linked source clauses rather than claiming vector search.

On backend restart, pending clarification and review states survive. Previously
running or queued work becomes visibly `FAILED`; v1 does not automatically retry
an uncertain business command. The Agent checkpoint tests separately verify
that its waiting graph can resume across process restarts.

No GitHub issues or merges were performed for this implementation.

## Independent gate

The independent gate approved the replacement with no concrete goal blockers.
It reproduced the 17 frontend tests, inspected three persisted QA tasks and
confirmed approved snapshots match their reviewed reports. Two stale legacy
runtime references in the project guides were corrected after the review.
The reviewer did not have a separate raw Aside click-log artifact; the manual
ledger and saved screenshots are recorded in `v1-validation.md`.
