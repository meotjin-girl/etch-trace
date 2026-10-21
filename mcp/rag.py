"""Document MCP: resolve exact document section IDs directly from PostgreSQL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NotRequired, TypedDict

import psycopg
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from openai import OpenAI
from psycopg.rows import class_row
from pydantic import TypeAdapter
from sop_rerank import CANDIDATE_K, rerank
from sop_vectors import MODEL, Embedder, Hit, retrieve


class Document(TypedDict):
    id: str
    title: str
    text: str
    is_demo: NotRequired[bool]
    source: NotRequired[str]
    revision: NotRequired[str]
    notice: NotRequired[str]
    distance: NotRequired[float]


auth_token = os.environ.get("RAG_MCP_TOKEN")
mcp = FastMCP(
    "etch-rag",
    version="1.0.0",
    auth=(
        StaticTokenVerifier(tokens={auth_token: {"client_id": "trace-agent", "sub": "trace-team"}})
        if auth_token
        else None
    ),
)


@dataclass(frozen=True, slots=True)
class DocumentRow:
    id: str
    data: str


@mcp.tool
def search_documents(document_ids: list[str]) -> list[Document]:
    """Resolve exact IDs, omitting unknown IDs and preserving unique input order."""
    if not document_ids:
        return []
    with psycopg.Connection[DocumentRow].connect(
        os.environ["DATABASE_URL"], row_factory=class_row(DocumentRow)
    ) as connection:
        rows = connection.execute(
            "SELECT id, data::text FROM etch_documents WHERE id = ANY(%s)",
            (document_ids,),
        ).fetchall()
    documents: dict[str, Document] = {
        row.id: {**TypeAdapter(Document).validate_json(row.data), "id": row.id} for row in rows
    }
    return [
        documents[document_id]
        for document_id in dict.fromkeys(document_ids)
        if document_id in documents
    ]


@mcp.tool
def search_sop(query: str) -> list[Document]:
    """Search SOP/OCAP text using the prebuilt embedding index and clause reranker.

    Run rag-ingest before serving queries. Search only embeds the query,
    retrieves twenty candidates, then reranks three source clauses. It never
    refreshes or prunes the corpus.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must contain text")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for SOP embedding and reranking")
    database_url = os.environ.get("SOP_DATABASE_URL")
    if not database_url:
        raise RuntimeError("SOP_DATABASE_URL is required for SOP retrieval")

    with OpenAI(timeout=60.0, max_retries=0) as client:
        embedder = Embedder(client, MODEL)
        vectors, _ = embedder.embed([query])
        with psycopg.connect(database_url) as connection:
            candidates = retrieve(connection, vectors[0], CANDIDATE_K)
        if len(candidates) < 3:
            raise RuntimeError(
                f"SOP index returned {len(candidates)} candidates; at least three are required"
            )
        hits: list[Hit] = rerank(client, query, candidates).hits

    return [
        {
            "id": hit.id,
            "title": f"{hit.document_title} · {hit.section_title}",
            "text": hit.text,
            "is_demo": hit.is_demo,
            "source": hit.source,
            "revision": hit.revision,
            "notice": hit.notice,
            "distance": hit.distance,
        }
        for hit in hits
    ]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
