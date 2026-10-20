"""OpenAI embeddings and isolated pgvector storage; no Agent or MCP changes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final

import psycopg
from openai import OpenAI
from psycopg.rows import TupleRow, class_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict
from sop_chunks import Chunk


class EmbeddingModel(StrEnum):
    SMALL = "text-embedding-3-small"
    LARGE = "text-embedding-3-large"


MODEL: Final = EmbeddingModel.SMALL
DIMENSIONS: Final = 1536


class Hit(Chunk):
    distance: float


class IngestResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    documents: int
    chunks: int
    embedded: int
    tokens: int
    model: EmbeddingModel


@dataclass(frozen=True, slots=True)
class StoredChunk:
    id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class HitRow:
    data: str
    distance: float


@dataclass(frozen=True, slots=True)
class Embedding:
    values: list[float]
    model: EmbeddingModel = MODEL


@dataclass(frozen=True, slots=True)
class Embedder:
    client: OpenAI
    model: EmbeddingModel = MODEL

    def embed(self, texts: list[str]) -> tuple[list[Embedding], int]:
        response = self.client.embeddings.create(
            model=self.model, input=texts, dimensions=DIMENSIONS, encoding_format="float"
        )
        vectors = [
            Embedding(values=item.embedding, model=self.model)
            for item in sorted(response.data, key=lambda item: item.index)
        ]
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding response count differs from input")
        return vectors, response.usage.total_tokens


def ingest(
    connection: psycopg.Connection[TupleRow],
    embedder: Embedder,
    chunks: list[Chunk],
) -> IngestResult:
    """Atomically refresh the experiment corpus, reusing unchanged embeddings."""
    _ = connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    _ = connection.execute("""
        CREATE TABLE IF NOT EXISTS sop_rag_model_chunks (
            id text NOT NULL,
            data jsonb NOT NULL,
            content_hash text NOT NULL,
            model text NOT NULL,
            embedding vector(1536) NOT NULL,
            PRIMARY KEY (model, id)
        )
    """)
    with connection.cursor(row_factory=class_row(StoredChunk)) as cursor:
        stored = cursor.execute(
            "SELECT id, content_hash FROM sop_rag_model_chunks WHERE model = %s", (embedder.model,)
        ).fetchall()
    hashes = {row.id: row.content_hash for row in stored}
    changed = [chunk for chunk in chunks if hashes.get(chunk.id) != chunk.content_hash]
    tokens = 0
    if changed:
        vectors, tokens = embedder.embed([chunk.embedding_text for chunk in changed])
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO sop_rag_model_chunks (id, data, content_hash, model, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                ON CONFLICT (model, id) DO UPDATE SET
                    data = EXCLUDED.data, content_hash = EXCLUDED.content_hash,
                    model = EXCLUDED.model, embedding = EXCLUDED.embedding
            """,
                [
                    (
                        chunk.id,
                        Jsonb(chunk.model_dump()),
                        chunk.content_hash,
                        embedder.model,
                        json.dumps(vector.values, allow_nan=False),
                    )
                    for chunk, vector in zip(changed, vectors, strict=True)
                ],
            )
    _ = connection.execute(
        "DELETE FROM sop_rag_model_chunks WHERE model = %s AND NOT (id = ANY(%s))",
        (embedder.model, [chunk.id for chunk in chunks]),
    )
    return IngestResult(
        documents=len({chunk.document_id for chunk in chunks}),
        chunks=len(chunks),
        embedded=len(changed),
        tokens=tokens,
        model=embedder.model,
    )


def retrieve(
    connection: psycopg.Connection[TupleRow],
    vector: Embedding,
    top_k: int | None = 3,
) -> list[Hit]:
    """Return exact cosine nearest neighbors, with stable ordering for ties."""
    if top_k is not None and top_k < 1:
        raise RuntimeError("top_k must be positive")
    with connection.cursor(row_factory=class_row(HitRow)) as cursor:
        rows = cursor.execute(
            """
            SELECT data::text, embedding <=> %s::vector AS distance
            FROM sop_rag_model_chunks WHERE model = %s
            ORDER BY distance, id LIMIT %s
        """,
            (json.dumps(vector.values, allow_nan=False), vector.model, top_k),
        ).fetchall()
    return [
        Hit.model_validate(
            {**Chunk.model_validate_json(row.data).model_dump(), "distance": row.distance}
        )
        for row in rows
    ]
