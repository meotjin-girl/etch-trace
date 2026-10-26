from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openai import OpenAI
from pydantic import JsonValue, TypeAdapter, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from sop_chunks import load_chunks
from sop_experiment import Question
from sop_rerank import RankedSections, ranking_format, rerank, select_sections
from sop_vectors import Hit


def candidates() -> list[Hit]:
    return [
        Hit(
            id=f"SOP-TEST#{index}",
            document_id="SOP-TEST",
            document_title="test",
            section_title=str(index),
            text=str(index),
            source="sop/test.md",
            revision="0.1",
            notice="[demo]",
            distance=index / 10,
        )
        for index in range(1, 5)
    ]


class RerankTest(unittest.TestCase):
    def test_selection_preserves_original_evidence_when_reordering_ids(self) -> None:
        # Given
        hits = candidates()
        ranking = RankedSections(section_ids=["SOP-TEST#4", "SOP-TEST#1", "SOP-TEST#3"])
        # When
        selected = select_sections(ranking, hits)
        # Then
        self.assertEqual(selected, [hits[3], hits[0], hits[2]])
        self.assertIs(selected[0], hits[3])

    def test_selection_rejects_ids_outside_candidate_pool(self) -> None:
        # Given
        ranking = RankedSections(section_ids=["SOP-TEST#1", "SOP-TEST#2", "UNKNOWN"])
        # When / Then
        with self.assertRaises(RuntimeError):
            _ = select_sections(ranking, candidates())

    def test_selection_rejects_duplicate_ids(self) -> None:
        # Given
        ranking = RankedSections(section_ids=["SOP-TEST#1", "SOP-TEST#1", "SOP-TEST#3"])
        # When / Then
        with self.assertRaises(RuntimeError):
            _ = select_sections(ranking, candidates())

    def test_schema_requires_exactly_three_sections(self) -> None:
        # Given
        ids = ["SOP-TEST#1", "SOP-TEST#2"]
        # When / Then
        with self.assertRaises(ValidationError):
            _ = RankedSections(section_ids=ids)

    def test_output_schema_only_offers_candidate_ids(self) -> None:
        # Given
        text_format = ranking_format(candidates())
        # When
        field = TypeAdapter(dict[str, JsonValue]).validate_python(
            text_format.model_json_schema()["properties"]["section_ids"]
        )
        # Then
        self.assertEqual(
            field["items"],
            {"type": "string", "enum": [f"SOP-TEST#{index}" for index in range(1, 5)]},
        )
        self.assertEqual((field["minItems"], field["maxItems"]), (3, 3))

    def test_rerank_retries_once_after_duplicate_ids(self) -> None:
        # Given: the first structured answer repeats an ID, the second is valid.
        hits = candidates()
        text_format = ranking_format(hits)

        def answer(ids: list[str]) -> SimpleNamespace:
            usage = SimpleNamespace(input_tokens=10, output_tokens=2)
            return SimpleNamespace(output_parsed=text_format(section_ids=ids), usage=usage)

        replies = [
            answer(["SOP-TEST#1", "SOP-TEST#1", "SOP-TEST#2"]),
            answer(["SOP-TEST#3", "SOP-TEST#1", "SOP-TEST#2"]),
        ]
        with (
            OpenAI(api_key="test-unused") as client,
            patch.object(client.responses, "parse", side_effect=replies) as parse,
        ):
            # When
            result = rerank(client, "query", hits)
        # Then
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(result.hits, [hits[2], hits[0], hits[1]])
        self.assertEqual((result.input_tokens, result.output_tokens), (20, 4))

    def test_rerank_fails_with_returned_ids_after_second_duplicate(self) -> None:
        # Given
        hits = candidates()
        text_format = ranking_format(hits)
        reply = SimpleNamespace(
            output_parsed=text_format(section_ids=["SOP-TEST#1", "SOP-TEST#1", "SOP-TEST#2"]),
            usage=SimpleNamespace(input_tokens=10, output_tokens=2),
        )
        with (
            OpenAI(api_key="test-unused") as client,
            patch.object(client.responses, "parse", return_value=reply) as parse,
            # When / Then
            self.assertRaisesRegex(RuntimeError, "SOP-TEST#1, SOP-TEST#1, SOP-TEST#2"),
        ):
            _ = rerank(client, "query", hits)
        self.assertEqual(parse.call_count, 2)

    def test_additional_questions_reference_real_sections(self) -> None:
        # Given
        ids = {chunk.id for chunk in load_chunks(ROOT / "sop-ocap")}
        # When
        questions = TypeAdapter(list[Question]).validate_json(
            (ROOT / "mcp/sop_questions_holdout.json").read_bytes()
        )
        # Then
        self.assertEqual(len({question.id for question in questions}), 10)
        self.assertEqual(sum(bool(question.expected_ids) for question in questions), 8)
        self.assertTrue(all(set(question.expected_ids) <= ids for question in questions))
