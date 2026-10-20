"""Transparent Korean/English extraction, without model-generated measurements."""

import re

from .models import Context


def parse_question(text: str, existing: Context | None = None) -> Context:
    """Merge newly stated fields and measurements into the current context."""
    current = existing or Context()
    data = current.model_dump()
    upper = text.upper()
    equipment = re.search(r"(?<![A-Z0-9])ETCH[\s_-]?(\d+)(?![A-Z0-9])", upper)
    chamber = re.search(r"(?<![A-Z0-9])CH[\s_-]?([A-Z])(?![A-Z0-9])", upper)
    recipe = re.search(
        r"(?<![A-Z0-9])(?!ETCH[\s_-]|CH[\s_-])([A-Z]{2,5}-\d{2,4})(?![A-Z0-9])",
        upper,
    )
    if equipment:
        data["equipment"] = f"ETCH-{equipment.group(1)}"
    if chamber:
        data["chamber"] = f"CH-{chamber.group(1)}"
    if recipe:
        data["recipe"] = recipe.group(1)

    metrics = dict(current.metrics)
    patterns = {
        "endpoint_sec": r"(?:endpoint|엔드포인트)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:초|sec|s\b)",
        "etch_rate_nm_min": r"(?:etch\s*rate|식각률|식각\s*속도)[^\d]{0,15}(\d+(?:\.\d+)?)",
        "rf_reflected_w": (
            r"(?:rf\s*)?(?:reflected(?:\s*power)?|반사\s*전력)"
            r"[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:w|와트)?"
        ),
        "pressure_mtorr": r"(?:pressure|압력)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:mtorr)?",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            metrics[name] = float(match.group(1))
    data["metrics"] = metrics

    lower = text.lower()
    symptoms = list(filter(None, (current.symptom or "").split(" · ")))
    rules = [
        (r"endpoint|엔드포인트", r"지연|증가|늦|delay|increas|late", "endpoint 지연"),
        (r"etch\s*rate|식각률|식각\s*속도", r"저하|감소|낮|drop|decreas|low", "etch rate 저하"),
        (r"reflected|반사\s*전력", r"상승|증가|높|ris|increas|high", "RF reflected power 상승"),
        (r"pressure|압력", r"불안정|변동|상승|저하|unstable|fluctuat|high|low",
         "chamber pressure 이상"),
    ]
    for subject, change, symptom in rules:
        if re.search(subject, lower) and re.search(change, lower) and symptom not in symptoms:
            symptoms.append(symptom)
    if symptoms:
        data["symptom"] = " · ".join(symptoms)
    return Context.model_validate(data)


def missing_fields(context: Context) -> list[str]:
    """Require an observed symptom and at least one search scope."""
    missing = []
    if not context.symptom:
        missing.append("symptom")
    if not any((context.equipment, context.chamber, context.recipe)):
        missing.append("scope")
    return missing


def clarification_message(missing: list[str]) -> str:
    """Ask only for the missing search conditions."""
    questions = []
    if "symptom" in missing:
        questions.append("어떤 이상 현상이 관찰됐나요? (예: endpoint 지연, etch rate 저하)")
    if "scope" in missing:
        questions.append("어느 장비·챔버·레시피에서 발생했나요? 아는 항목만 알려주세요.")
    return " ".join(questions)
