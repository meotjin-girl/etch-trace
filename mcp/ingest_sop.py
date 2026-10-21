"""Explicit corpus refresh: docker compose run --rm rag-ingest."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from openai import OpenAI
from sop_chunks import load_chunks
from sop_vectors import MODEL, Embedder, ingest


def main() -> None:
    """Embed changed sections and atomically replace this model's corpus."""
    chunks = load_chunks(Path(os.environ["SOP_DOCUMENTS_DIR"]))
    with (
        OpenAI(timeout=60.0, max_retries=0) as client,
        psycopg.connect(os.environ["SOP_DATABASE_URL"]) as connection,
    ):
        result = ingest(connection, Embedder(client, MODEL), chunks)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
