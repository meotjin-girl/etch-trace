# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]>=3.2,<4", "pydantic>=2,<3"]
# ///
"""Run: DATABASE_URL=postgresql://... uv run db/seed.py [schema.sql]."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import LiteralString

import psycopg
from psycopg.types.json import Jsonb
from pydantic import JsonValue, TypeAdapter


def seed(database_url: str, schema_file: Path) -> None:
    """Apply the schema and upsert the demo fixtures in one transaction."""
    data_dir = Path(__file__).resolve().parent
    with psycopg.connect(database_url) as connection:
        _ = connection.execute(schema_file.read_bytes())
        with connection.cursor() as cursor:
            statements: tuple[tuple[str, LiteralString], ...] = (
                (
                    "cases.json",
                    "INSERT INTO etch_cases (id, data) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                ),
                (
                    "documents.json",
                    "INSERT INTO etch_documents (id, data) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                ),
            )
            for filename, statement in statements:
                records = TypeAdapter(list[dict[str, JsonValue]]).validate_json(
                    (data_dir / filename).read_bytes()
                )
                cursor.executemany(
                    statement, [(record["id"], Jsonb(record)) for record in records]
                )


if __name__ == "__main__":
    schema = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("schema.sql")
    seed(os.environ["DATABASE_URL"], schema)
