"""Pure frontend-compatible evidence scoring and population statistics."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Final, NotRequired, TypedDict


METRIC_UNITS: Final = {
    "endpoint_sec": "sec",
    "etch_rate_nm_min": "nm/min",
    "rf_reflected_w": "W",
    "pressure_mtorr": "mTorr",
}


class Case(TypedDict):
    id: str
    equipment: str
    chamber: str
    recipe: str
    symptom: str
    metrics: dict[str, float]
    cause: str
    action: str
    docs: list[str]
    is_demo: NotRequired[bool]
    source: NotRequired[str]
    metric_units: NotRequired[dict[str, str]]


class ScoredCase(Case):
    score: float


class Context(TypedDict, total=False):
    equipment: str
    chamber: str
    recipe: str
    symptom: str
    metrics: dict[str, float]


class MetricAnalysis(TypedDict):
    key: str
    value: float
    mean: float
    std: float
    deltaPct: float
    z: float | None
    severity: str
    supporting_case_ids: list[str]
    unit: str


def similarity(case: Case, context: Context) -> float:
    """Match frontend weights, substring tokens, and shared-metric bonus."""
    score = 0.0
    if case["equipment"] == context.get("equipment"):
        score += 0.30
    if case["chamber"] == context.get("chamber"):
        score += 0.20
    if case["recipe"] == context.get("recipe"):
        score += 0.25
    tokens = [
        token
        for token in re.split(r"\s+|·", context.get("symptom", "").lower())
        if len(token) > 1
    ]
    target = case["symptom"].lower()
    score += min(0.20, sum(token in target for token in tokens) * 0.05)
    if any(key in case["metrics"] for key in context.get("metrics", {})):
        score += 0.05
    return min(1.0, score)


def search_cases(cases: list[Case], context: Context) -> list[ScoredCase]:
    """Return at most five cases with score >= .25, preserving tie order."""
    scored: list[ScoredCase] = [
        {**case, "score": similarity(case, context)} for case in cases
    ]
    return sorted(
        (case for case in scored if case["score"] >= 0.25),
        key=lambda case: case["score"],
        reverse=True,
    )[:5]


def analyze_metrics(
    cases: Sequence[Case], metrics: dict[str, float]
) -> list[MetricAnalysis]:
    """Compute frontend population statistics, retaining each observation's ID."""
    results: list[MetricAnalysis] = []
    for key, value in metrics.items():
        observations = [
            (case["id"], case["metrics"][key])
            for case in cases
            if key in case["metrics"] and math.isfinite(case["metrics"][key])
        ]
        if not observations:
            continue
        values = [observation for _, observation in observations]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((item - mean) ** 2 for item in values) / len(values))
        delta_pct = (value - mean) / mean * 100 if mean else 0.0
        z = (value - mean) / std if std else None
        severity = "정상"
        if abs(z or 0) >= 2 or abs(delta_pct) >= 20:
            severity = "비정상"
        elif abs(z or 0) >= 1 or abs(delta_pct) >= 10:
            severity = "주의"
        results.append(
            {
                "key": key,
                "value": value,
                "mean": mean,
                "std": std,
                "deltaPct": delta_pct,
                "z": z,
                "severity": severity,
                "supporting_case_ids": [case_id for case_id, _ in observations],
                "unit": METRIC_UNITS.get(key, ""),
            }
        )
    return results
