from __future__ import annotations

import json
from pathlib import Path

from .models import ComparableCase, HistoricalCase, InvestigationRequest


DATA_DIR = Path(__file__).resolve().parent / "data"


class InvestigationRepository:
    """Small file-backed repository; replace this adapter with MES/FDC/EDMS clients."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir

    def cases(self) -> list[HistoricalCase]:
        raw = json.loads((self.data_dir / "historical_cases.json").read_text(encoding="utf-8"))
        return [HistoricalCase.model_validate(item) for item in raw]

    def documents(self) -> dict[str, dict[str, str]]:
        return json.loads((self.data_dir / "documents.json").read_text(encoding="utf-8"))

    def find_comparable(
        self, request: InvestigationRequest, limit: int = 5
    ) -> list[ComparableCase]:
        scored: list[ComparableCase] = []
        symptom_tokens = _tokens(request.symptom or "")
        for case in self.cases():
            score = 0.0
            reasons: list[str] = []
            if case.equipment_id == request.equipment_id:
                score += 0.25
                reasons.append("동일 장비")
            if case.chamber_id == request.chamber_id:
                score += 0.20
                reasons.append("동일 챔버")
            if case.recipe == request.recipe:
                score += 0.25
                reasons.append("동일 레시피")
            if request.product and case.product == request.product:
                score += 0.10
                reasons.append("동일 제품")
            overlap = _jaccard(symptom_tokens, _tokens(case.symptom))
            if overlap:
                score += 0.15 * overlap
                reasons.append(f"증상 유사도 {overlap:.2f}")
            shared_metrics = set(request.metrics) & set(case.metrics)
            if shared_metrics:
                score += 0.05 * min(1.0, len(shared_metrics) / max(1, len(request.metrics)))
                reasons.append(f"공통 계측 {len(shared_metrics)}개")
            if score >= 0.25:
                scored.append(
                    ComparableCase(case=case, similarity=round(score, 3), match_reasons=reasons)
                )
        return sorted(scored, key=lambda item: item.similarity, reverse=True)[:limit]


def _tokens(text: str) -> set[str]:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {token for token in normalized.split() if len(token) > 1}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)

