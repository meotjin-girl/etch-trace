from __future__ import annotations

import os
import sys
import tempfile
import unittest
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import psycopg
from openai import OpenAI
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow
from pydantic import TypeAdapter
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from sop_chunks import Chunk, load_chunks, parse_document
from sop_experiment import QUESTIONS, Question, app, score
from sop_rerank import RerankResult
from sop_vectors import (
    DIMENSIONS,
    Embedder,
    Embedding,
    EmbeddingModel,
    Hit,
    IngestResult,
    ingest,
    retrieve,
)


def sample_chunk(section: str = "1") -> Chunk:
    return Chunk(
        id=f"SOP-TEST-01#{section}",
        document_id="SOP-TEST-01",
        document_title="SOP-TEST-01 test",
        section_title=section,
        text="body",
        source="sop/SOP-TEST-01.md",
        revision="0.1",
        notice="[demo]",
    )


@contextmanager
def vector_database() -> Generator[psycopg.Connection[TupleRow]]:
    with (
        psycopg.connect(os.environ["SOP_TEST_DATABASE_URL"]) as connection,
        connection.transaction(force_rollback=True),
    ):
        schema = sql.Identifier(f"sop_test_{uuid4().hex}")
        _ = connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        _ = connection.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(schema))
        yield connection


class ChunkTest(unittest.TestCase):
    def test_cli_registers_commands_without_loading_credentials(self) -> None:
        # Given
        runner = CliRunner()
        # When
        result = runner.invoke(app, ["--help"])
        # Then
        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.exception)

    def test_cli_rejects_empty_query_before_calling_api(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            _ = env_file.write_text("", encoding="utf-8")
            runner = CliRunner()
            # When
            with patch("sop_experiment.openai_client") as client:
                result = runner.invoke(app, ["search", "  ", "--env-file", str(env_file)])
            # Then
            self.assertEqual(result.exit_code, 2)
            client.assert_not_called()

    def test_cli_rejects_rerank_limit_change_before_calling_api(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            _ = env_file.write_text("", encoding="utf-8")
            runner = CliRunner()
            # When
            with patch("sop_experiment.openai_client") as client:
                result = runner.invoke(
                    app,
                    [
                        "search",
                        "test",
                        "--method",
                        "rerank",
                        "--top-k",
                        "5",
                        "--env-file",
                        str(env_file),
                    ],
                )
            # Then
            self.assertEqual(result.exit_code, 2)
            client.assert_not_called()

    def test_parser_keeps_parent_intro_tables_and_stable_sections(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SOP-TEST-01.md"
            _ = path.write_text(
                """# SOP-TEST-01 test

| 개정 | Rev 0.1 |

> [demo]

## 1. parent

intro

### 1.1 child

| key | value |
|---|---|
| a | b |

## 2. empty parent

### 2.1 step

1. one
2. two

## 3. 개정 이력

revision notes
""",
                encoding="utf-8",
            )
            # When
            chunks = parse_document(path)
        # Then
        self.assertEqual(
            [chunk.id for chunk in chunks],
            ["SOP-TEST-01#1", "SOP-TEST-01#1.1", "SOP-TEST-01#2.1"],
        )
        self.assertEqual(chunks[0].text, "intro")
        self.assertEqual(chunks[1].text, "| key | value |\n|---|---|\n| a | b |")
        self.assertEqual(chunks[2].text, "1. one\n2. two")
        self.assertEqual(chunks[1].section_title, "parent / 1.1 child")
        self.assertEqual(chunks[1].notice, "[demo]")

    def test_parser_reads_sop_ocap_header_table_and_loader_keeps_ocap(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _ = (root / "OCAP-TEST-01.md").write_text(
                "# OCAP-TEST-01 test\n\n| 담당 팀 | 버전 | 최근 개정 |\n| --- | --- | --- |\n"
                "| Etch설비기술팀 | 1.1 | 2026-10-20 |\n\n## 1. 적용 범위\n\nbody\n",
                encoding="utf-8",
            )
            # When
            chunks = load_chunks(root)
        # Then
        self.assertEqual([chunk.id for chunk in chunks], ["OCAP-TEST-01#1"])
        self.assertEqual(chunks[0].revision, "1.1 (2026-10-20)")

    def test_loader_excludes_notes_when_only_sop_is_evidence(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "00_notes.md", "SOP-TEST-01.md"):
                _ = (root / name).write_text(
                    "# SOP-TEST-01 test\n| 개정 | Rev 0.1 |\n## 1. section\nbody",
                    encoding="utf-8",
                )
            # When
            chunks = load_chunks(root)
        # Then
        self.assertEqual([chunk.id for chunk in chunks], ["SOP-TEST-01#1"])

    def test_hash_changes_when_source_metadata_changes(self) -> None:
        # Given
        chunk = sample_chunk()
        # When
        changed = chunk.model_copy(update={"revision": "0.2"})
        # Then
        self.assertNotEqual(chunk.content_hash, changed.content_hash)

    def test_real_corpus_preserves_existing_document_ids(self) -> None:
        # Given
        legacy = TypeAdapter(list[dict[str, str | bool]]).validate_json(
            (ROOT / "db/documents.json").read_bytes()
        )
        # When
        chunks = load_chunks(ROOT / "sop-ocap")
        # Then
        self.assertEqual(len({chunk.document_id for chunk in chunks}), 7)
        self.assertTrue({document["id"] for document in legacy} <= {chunk.id for chunk in chunks})
        self.assertTrue(all(chunk.is_demo and chunk.notice for chunk in chunks))

    def test_evaluation_requires_every_expected_section(self) -> None:
        # Given
        question = Question(
            id="multi",
            category="multi",
            query="test",
            expected_ids=["SOP-TEST-01#1", "SOP-TEST-01#2"],
        )
        hit = Hit.model_validate({**sample_chunk().model_dump(), "distance": 0.1})
        # When
        passed = score(question, [hit])
        # Then
        self.assertFalse(passed)

    def test_out_of_scope_is_not_counted_as_retrieval_success(self) -> None:
        # Given
        question = Question(id="outside", category="out_of_scope", query="test", expected_ids=[])
        # When
        passed = score(
            question, [Hit.model_validate({**sample_chunk().model_dump(), "distance": 0.1})]
        )
        # Then
        self.assertIsNone(passed)

    def test_evaluation_ids_exist_and_categories_have_planned_counts(self) -> None:
        # Given
        ids = {chunk.id for chunk in load_chunks(ROOT / "sop-ocap")}
        # When
        questions = TypeAdapter(list[Question]).validate_json(QUESTIONS.read_bytes())
        # Then
        self.assertEqual(len({question.id for question in questions}), 15)
        for category, count in (
            ("direct", 5),
            ("paraphrase", 5),
            ("multi", 3),
            ("out_of_scope", 2),
        ):
            self.assertEqual(sum(question.category == category for question in questions), count)
        self.assertTrue(all(set(question.expected_ids) <= ids for question in questions))


@unittest.skipUnless(os.getenv("SOP_TEST_DATABASE_URL"), "SOP_TEST_DATABASE_URL is required")
class VectorTest(unittest.TestCase):
    def test_search_reads_prebuilt_index_without_source_files_or_writes(self) -> None:
        import rag

        # Given: a committed index, no source directory, and read-only search connections.
        schema_name = f"sop_read_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        base_url = os.environ["SOP_TEST_DATABASE_URL"]
        with psycopg.connect(base_url) as connection, OpenAI(api_key="test-unused") as client:
            _ = connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            _ = connection.execute(sql.SQL("SET search_path TO {}, public").format(schema))
            vector = Embedding([1.0] * DIMENSIONS)
            with patch("sop_vectors.Embedder.embed", return_value=([vector] * 3, 3)):
                _ = ingest(connection, Embedder(client), [sample_chunk(str(n)) for n in (1, 2, 3)])
            connection.commit()
            read_url = make_conninfo(
                base_url,
                options=f"-csearch_path={schema_name},public -cdefault_transaction_read_only=on",
            )

            def rank(_client: OpenAI, _query: str, candidates: list[Hit]) -> RerankResult:
                return RerankResult(candidates, 0, 0, 0.0)

            try:
                with (
                    patch.dict(
                        os.environ,
                        {
                            "SOP_DATABASE_URL": read_url,
                            "SOP_DOCUMENTS_DIR": "/nonexistent-source-directory",
                            "OPENAI_API_KEY": "test-unused",
                        },
                    ),
                    patch("sop_vectors.Embedder.embed", return_value=([vector], 1)),
                    patch("rag.rerank", side_effect=rank),
                ):
                    # When
                    documents = rag.search_sop("test")
                # Then
                self.assertEqual(
                    [document["id"] for document in documents],
                    ["SOP-TEST-01#1", "SOP-TEST-01#2", "SOP-TEST-01#3"],
                )
            finally:
                _ = connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))
                connection.commit()

    def test_parallel_ingest_waits_before_embedding(self) -> None:
        # Given: a committed schema and the first refresh held inside embedding.
        url = os.environ["SOP_TEST_DATABASE_URL"]
        schema = sql.Identifier(f"sop_parallel_{uuid4().hex}")
        entered, release = Event(), Event()
        with psycopg.connect(url) as setup, OpenAI(api_key="test-unused") as client:
            _ = setup.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            _ = setup.execute(sql.SQL("SET search_path TO {}, public").format(schema))
            _ = ingest(setup, Embedder(client), [])
        calls: list[list[str]] = []

        def embed(_self: Embedder, texts: list[str]) -> tuple[list[Embedding], int]:
            calls.append(texts)
            entered.set()
            if len(calls) == 1 and not release.wait(timeout=5):
                raise TimeoutError("first ingestion was not released")
            return [Embedding([1.0] * DIMENSIONS)], 1

        def first_refresh() -> IngestResult:
            with psycopg.connect(url) as connection, OpenAI(api_key="test-unused") as client:
                _ = connection.execute(sql.SQL("SET search_path TO {}, public").format(schema))
                return ingest(connection, Embedder(client), [sample_chunk()])

        try:
            with (
                patch("sop_vectors.Embedder.embed", autospec=True, side_effect=embed),
                ThreadPoolExecutor(max_workers=1) as pool,
            ):
                first = pool.submit(first_refresh)
                try:
                    self.assertTrue(entered.wait(timeout=5))
                    # When: another connection attempts refresh before commit.
                    with (
                        psycopg.connect(url) as second,
                        OpenAI(api_key="test-unused") as client,
                    ):
                        _ = second.execute(sql.SQL("SET search_path TO {}, public").format(schema))
                        _ = second.execute("SET lock_timeout = '100ms'")
                        # The lock timeout itself is the behavior under test,
                        # not a scheduling sleep or a poll for another thread.
                        with self.assertRaises(psycopg.errors.LockNotAvailable):
                            _ = ingest(second, Embedder(client), [sample_chunk()])
                        second.rollback()
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=5).embedded, 1)
            # Then: the competing refresh never reached embedding.
            self.assertEqual(len(calls), 1)
        finally:
            with psycopg.connect(url) as cleanup:
                _ = cleanup.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

    def test_ingest_reuses_unchanged_embeddings(self) -> None:
        # Given
        with vector_database() as connection, OpenAI(api_key="test-unused") as client:
            embedder = Embedder(client)
            with patch(
                "sop_vectors.Embedder.embed", return_value=([Embedding([1.0] * DIMENSIONS)], 1)
            ):
                _ = ingest(connection, embedder, [sample_chunk()])
            # When
            with patch("sop_vectors.Embedder.embed") as embeddings:
                result = ingest(connection, embedder, [sample_chunk()])
            # Then
            self.assertEqual(result.embedded, 0)
            embeddings.assert_not_called()

    def test_ingest_updates_changed_sections_and_prunes_removed_sections(self) -> None:
        # Given
        with vector_database() as connection, OpenAI(api_key="test-unused") as client:
            embedder = Embedder(client)
            vector = Embedding([1.0] * DIMENSIONS)
            with patch("sop_vectors.Embedder.embed", return_value=([vector, vector], 2)):
                _ = ingest(connection, embedder, [sample_chunk(), sample_chunk("2")])
            changed = sample_chunk().model_copy(update={"text": "updated"})
            # When
            with patch("sop_vectors.Embedder.embed", return_value=([vector], 1)):
                result = ingest(connection, embedder, [changed])
            # Then
            self.assertEqual(result.embedded, 1)
            hits = retrieve(connection, vector)
            self.assertEqual([hit.id for hit in hits], [changed.id])
            self.assertEqual(hits[0].text, "updated")

    def test_cosine_search_ranks_vectors_and_breaks_ties_by_id(self) -> None:
        # Given
        with vector_database() as connection, OpenAI(api_key="test-unused") as client:
            x = Embedding([1.0] + [0.0] * (DIMENSIONS - 1))
            y = Embedding([0.0, 1.0] + [0.0] * (DIMENSIONS - 2))
            with patch("sop_vectors.Embedder.embed", return_value=([y, x, x], 3)):
                _ = ingest(connection, Embedder(client), [sample_chunk(str(n)) for n in (1, 3, 2)])
            # When
            hits = retrieve(connection, x, 2)
            # Then
            self.assertEqual([hit.id for hit in hits], ["SOP-TEST-01#2", "SOP-TEST-01#3"])
            self.assertAlmostEqual(hits[0].distance, 0)

    def test_retrieval_isolates_models_with_identical_vectors_and_section_ids(self) -> None:
        # Given
        with vector_database() as connection, OpenAI(api_key="test-unused") as client:
            values = [1.0] * DIMENSIONS
            small = sample_chunk()
            large = small.model_copy(update={"text": "large-specific source"})
            for model, chunk in ((EmbeddingModel.SMALL, small), (EmbeddingModel.LARGE, large)):
                with patch(
                    "sop_vectors.Embedder.embed", return_value=([Embedding(values, model)], 1)
                ):
                    _ = ingest(connection, Embedder(client, model), [chunk])
            # When
            hits = retrieve(connection, Embedding(values, EmbeddingModel.SMALL))
            # Then
            self.assertEqual([hit.text for hit in hits], [small.text])

    def test_ingest_preserves_other_models_when_pruning_deleted_sections(self) -> None:
        # Given
        with vector_database() as connection, OpenAI(api_key="test-unused") as client:
            values = [1.0] * DIMENSIONS
            for model in (EmbeddingModel.SMALL, EmbeddingModel.LARGE):
                vectors = [Embedding(values, model)] * 2
                with patch("sop_vectors.Embedder.embed", return_value=(vectors, 2)):
                    _ = ingest(
                        connection, Embedder(client, model), [sample_chunk(), sample_chunk("2")]
                    )
            # When
            _ = ingest(connection, Embedder(client, EmbeddingModel.LARGE), [sample_chunk()])
            # Then
            large_hits = retrieve(connection, Embedding(values, EmbeddingModel.LARGE))
            small_hits = retrieve(connection, Embedding(values, EmbeddingModel.SMALL))
            self.assertEqual([hit.id for hit in large_hits], [sample_chunk().id])
            self.assertEqual(
                [hit.id for hit in small_hits], [sample_chunk().id, sample_chunk("2").id]
            )


if __name__ == "__main__":
    _ = unittest.main()
