"""One-shot SOP/OCAP index refresh run by the compose rag-ingest service."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from openai import OpenAI
from sop_chunks import load_chunks
from sop_vectors import MODEL, Embedder, ingest


def main() -> None:
    """Embed changed sections and replace this model's corpus; unchanged sections cost nothing."""
    if not os.environ.get("OPENAI_API_KEY"):
        # Keep the stack usable without a key; search_sop reports itself unavailable.
        print("OPENAI_API_KEY is not set; skipping SOP indexing")
        return
    chunks = load_chunks(Path(os.environ["SOP_DOCUMENTS_DIR"]))
    with (
        OpenAI(timeout=60.0, max_retries=0) as client,
        psycopg.connect(os.environ["SOP_DATABASE_URL"]) as connection,
    ):
        result = ingest(connection, Embedder(client, MODEL), chunks)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
