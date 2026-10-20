from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from sop_chunks import load_chunks
from sop_experiment import Question
from sop_rerank import RankedSections, select_sections
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

    def test_additional_questions_reference_real_sections(self) -> None:
        # Given
        ids = {chunk.id for chunk in load_chunks(ROOT / "sop")}
        # When
        questions = TypeAdapter(list[Question]).validate_json(
            (ROOT / "mcp/sop_questions_holdout.json").read_bytes()
        )
        # Then
        self.assertEqual(len({question.id for question in questions}), 10)
        self.assertEqual(sum(bool(question.expected_ids) for question in questions), 8)
        self.assertTrue(all(set(question.expected_ids) <= ids for question in questions))
