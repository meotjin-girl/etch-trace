from __future__ import annotations

import re

from .models import InvestigationRequest


def parse_question(question: str, existing: dict | None = None) -> InvestigationRequest:
    """Extract search conditions from a Korean/English equipment question.

    This intentionally uses transparent rules so the demo runs without an LLM key.
    A production adapter can replace it with structured LLM extraction.
    """
    data = dict(existing or {})
    upper = question.upper()

    equipment = re.search(r"(?<![A-Z0-9])ETCH[\s_-]?(\d+)(?![A-Z0-9])", upper)
    chamber = re.search(r"(?<![A-Z0-9])CH[\s_-]?([A-Z])(?![A-Z0-9])", upper)
    recipe = re.search(
        r"(?<![A-Z0-9])(?!ETCH(?:\b|-)|CH(?:\b|-))([A-Z]{2,5}-\d{2,4})(?![A-Z0-9])",
        upper,
    )
    product = re.search(r"(?<![A-Z0-9])(P-[A-Z]\d{2,4})(?![A-Z0-9])", upper)
    lot = re.search(r"(?<![A-Z0-9])(L\d{6,}-?\d*)(?![A-Z0-9])", upper)
    event_time = re.search(
        r"\b(20\d{2}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2})?)?)\b",
        question,
    )

    if equipment:
        data["equipment_id"] = f"ETCH-{equipment.group(1)}"
    if chamber:
        data["chamber_id"] = f"CH-{chamber.group(1)}"
    if recipe:
        data["recipe"] = recipe.group(1)
    if product:
        data["product"] = product.group(1)
    if lot:
        data["lot_id"] = lot.group(1)
    if event_time:
        data["event_time"] = event_time.group(1).replace(" ", "T")

    metrics = dict(data.get("metrics") or {})
    _extract_metric(question, metrics, "endpoint_sec", [r"(?:endpoint|엔드포인트)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:초|sec|s\b)"])
    _extract_metric(question, metrics, "etch_rate_nm_min", [r"(?:etch\s*rate|식각률|식각\s*속도)[^\d]{0,15}(\d+(?:\.\d+)?)"])
    _extract_metric(question, metrics, "rf_reflected_w", [r"(?:rf\s*)?(?:reflected(?:\s*power)?|반사\s*전력)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:w|와트)?"])
    _extract_metric(question, metrics, "pressure_mtorr", [r"(?:pressure|압력)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:mtorr)?"])
    if metrics:
        data["metrics"] = metrics

    symptom_parts: list[str] = []
    lower = question.lower()
    if ("endpoint" in lower or "엔드포인트" in lower) and any(word in lower for word in ["지연", "증가", "늦"]):
        symptom_parts.append("endpoint 지연")
    if any(word in lower for word in ["etch rate", "식각률", "식각 속도"]) and any(word in lower for word in ["저하", "감소", "낮"]):
        symptom_parts.append("etch rate 저하")
    if any(word in lower for word in ["reflected", "반사 전력", "반사전력"]) and any(word in lower for word in ["상승", "증가", "높"]):
        symptom_parts.append("RF reflected power 상승")
    if ("pressure" in lower or "압력" in lower) and any(word in lower for word in ["불안정", "변동", "상승", "저하"]):
        symptom_parts.append("chamber pressure 이상")
    if symptom_parts:
        existing_symptom = data.get("symptom") or ""
        combined = [part for part in existing_symptom.split(" 및 ") if part]
        for part in symptom_parts:
            if part not in combined:
                combined.append(part)
        data["symptom"] = " 및 ".join(combined)

    return InvestigationRequest.model_validate(data)


def query_missing_fields(request: InvestigationRequest) -> list[str]:
    missing: list[str] = []
    if not request.symptom:
        missing.append("symptom")
    if not any([request.equipment_id, request.chamber_id, request.recipe, request.product]):
        missing.append("scope")
    return missing


def clarification_message(missing: list[str]) -> str:
    questions = []
    if "symptom" in missing:
        questions.append("어떤 이상 현상이 관찰됐나요? (예: endpoint 지연, etch rate 저하)")
    if "scope" in missing:
        questions.append("어느 장비·챔버·레시피에서 발생했나요? 아는 항목만 알려주세요.")
    return " ".join(questions)


def _extract_metric(question: str, metrics: dict[str, float], name: str, patterns: list[str]) -> None:
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            metrics[name] = float(match.group(1))
            return

