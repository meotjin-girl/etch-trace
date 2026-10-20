"""Document MCP: resolve exact document section IDs directly from PostgreSQL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NotRequired, TypedDict

import psycopg
from fastmcp import FastMCP
from psycopg.rows import class_row
from pydantic import TypeAdapter


class Document(TypedDict):
    id: str
    title: str
    text: str
    is_demo: NotRequired[bool]
    source: NotRequired[str]


mcp = FastMCP("etch-rag", version="1.0.0")


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
        row.id: {**TypeAdapter(Document).validate_json(row.data), "id": row.id}
        for row in rows
    }
    return [
        documents[document_id]
        for document_id in dict.fromkeys(document_ids)
        if document_id in documents
    ]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
