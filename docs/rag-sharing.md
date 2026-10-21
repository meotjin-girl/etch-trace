# Shared RAG MCP for team testing

The shared endpoint is `https://mcp-etch-trace-rag.dayeondev.com/mcp`.
It exposes MCP tools, not a PostgreSQL connection.
The host machine and its containers must remain running for teammates to connect.

## Corpus and retrieval

- Source: `sop-ocap/`, SOP 3 documents and OCAP 19 documents.
- README and the research note are excluded.
- Numbered level-two and level-three sections become chunks. Level-four
  scenarios stay inside their parent clause; tables are not split.
- IDs retain `{document ID}#{section}`, with source path, revision and demo flag.
- Embeddings: `text-embedding-3-small`, 1536 dimensions.
- Search: 20 cosine candidates, `gpt-4.1-mini` reranking, three source clauses.
- `search_sop(query)` only reads the index; it does not ingest documents.
- `search_documents(document_ids)` still reads the legacy `etch_documents`
  sample records. New semantic indexing does not migrate those IDs or cases.

## Owner setup

Use a git-ignored `.env.rag-share` with these values. Do not share its contents
or the Cloudflare connector token with clients.

```dotenv
OPENAI_API_KEY=<owner OpenAI key>
POSTGRES_PASSWORD=<local database password>
RAG_MCP_TOKEN=<team development Bearer token>
CF_RAG_TUNNEL_TOKEN=<dedicated Cloudflare tunnel connector token>
```

The dedicated remotely managed tunnel must have this ingress:

```json
{
  "ingress": [
    {
      "hostname": "mcp-etch-trace-rag.dayeondev.com",
      "path": "^/mcp/?$",
      "service": "http://rag-mcp:8000"
    },
    {"service": "http_status:404"}
  ]
}
```

Create a proxied CNAME for that hostname to `<tunnel UUID>.cfargotunnel.com`.
Do not reuse another application's connector token: connectors for one tunnel
must all be able to reach that tunnel's configured origins.

Start only the RAG services and their dependencies in a separate Compose
project, preserving other stacks and volumes:

```bash
chmod 600 .env.rag-share
docker compose -p trace-rag-share --env-file .env.rag-share \
  run --rm --build rag-ingest
docker compose -p trace-rag-share --env-file .env.rag-share \
  --profile rag-share up -d --build rag-mcp cloudflared
docker compose -p trace-rag-share --env-file .env.rag-share \
  --profile rag-share ps -a
```

The explicit first command runs `rag-ingest` before serving searches. Normal
Compose startup does not run ingest or require an embedding API key until
semantic search is used. Only changed chunks are embedded; removed clauses
are pruned for the selected model.
The new project has its own persistent vector database volume. No DB ports
are published. The separate legacy document database is seeded for exact-ID
lookups; backend, Agent and web are not started.
The connector uses HTTP/2 because QUIC handshakes timed out on the test network.

To refresh after updating documents, stop serving first so clients cannot
mix corpus versions across requests:

```bash
docker compose -p trace-rag-share --env-file .env.rag-share \
  --profile rag-share stop cloudflared rag-mcp
docker compose -p trace-rag-share --env-file .env.rag-share \
  run --rm --build rag-ingest
docker compose -p trace-rag-share --env-file .env.rag-share \
  --profile rag-share up -d rag-mcp cloudflared
```

`stop cloudflared` ends external access. Do not run `down -v`: the volumes
contain the prebuilt embeddings.

## Agent developer setup

Set these in the developer's own root `.env`. The owner provides the Bearer
token separately; clients do not need the owner's OpenAI or Cloudflare keys.
These settings require this branch's Agent Bearer-token support; the previous
Agent implementation does not send the token.

```dotenv
SHARED_RAG_MCP_URL=https://mcp-etch-trace-rag.dayeondev.com/mcp
RAG_MCP_TOKEN=<team development Bearer token>
```

Then recreate the Agent without starting or rebuilding a local RAG database:

```bash
docker compose up -d --no-deps --build agent
```

This assumes the developer's backend, business MCP and checkpoint database
are already running. Starting the complete default Compose stack also starts
local RAG services, but ingest remains explicit; use the command above for
remote-only Agent updates.

For a direct MCP smoke test from the repository:

```bash
uv run --project mcp python -c '
import os
import anyio
from fastmcp import Client

async def main():
    async with Client(
        "https://mcp-etch-trace-rag.dayeondev.com/mcp",
        auth=os.environ["RAG_MCP_TOKEN"],
        timeout=120,
    ) as client:
        result = await client.call_tool(
            "search_sop",
            {"query": "RF 반사전력이 반복 상승하면 접점과 calibration을 어떻게 확인하나요?"},
        )
        print(result.structured_content)

anyio.run(main)
'
```

Export `RAG_MCP_TOKEN` in the shell before that standalone command; `uv run`
does not automatically import the root `.env`.
The tools return evidence, not a final answer. Check source IDs and content
instead of pinning generated wording. The static token is for temporary team
testing, not a production identity system.

## Validation on October 21, 2026

- Dedicated Compose project: `trace-rag-share`. Dedicated Cloudflare tunnel:
  `trace-rag-share`, ID `bdec6bd3-9f92-47fd-a3d1-db6b08c03b6c`.
  The existing application's tunnel ingress was confirmed unchanged.
- PostgreSQL contains 22 documents, 240 chunks, 1536-dimensional vectors.
  Initial ingestion embedded 240 chunks using 43,451 tokens; a second ingestion
  embedded zero chunks and used zero embedding tokens.
- Both local MCP and the public HTTPS endpoint were exercised. The actual
  Agent adapter returned three clauses for each RF and GRID query, including
  the expected OCAP, source path, revision, and demo metadata. Legacy exact-ID
  lookup also succeeded.
- Anonymous MCP requests returned 401; non-MCP paths returned 404.
- Ten targeted parser/vector/search tests and two Agent MCP adapter tests passed.
  The search regression uses an actual PostgreSQL index with read-only
  connections and no source files.
- The wider MCP test run had 45 passing tests and three errors. All three
  reference the already-missing legacy `sop/` corpus:
  `test_real_corpus_preserves_existing_document_ids`,
  `test_evaluation_ids_exist_and_categories_have_planned_counts`,
  `test_additional_questions_reference_real_sections`.
  `git ls-tree -r HEAD sop` was empty before these changes. Those pre-existing
  tests and their old evaluation questions were not weakened or rewritten.
- MCP and Agent changed runtime files passed service-configured basedpyright
  with zero errors or warnings. Ruff, Compose configuration and whitespace
  checks passed. Frontend/backend suites and full investigation-report E2E
  were not run for this RAG-only change.
