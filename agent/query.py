"""Transparent Korean/English extraction, without model-generated measurements."""

import re

from .models import Context, PhysicsInputs


def _measurement(text: str, labels: str, units: str) -> tuple[float, str] | None:
    match = re.search(
        rf"(?:{labels})[^\d]{{0,24}}(\d+(?:\.\d+)?)\s*({units})",
        text,
        flags=re.IGNORECASE,
    )
    return (float(match.group(1)), match.group(2).lower()) if match else None


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

    physics = current.physics.model_dump()
    sources = dict(current.physics.sources)
    duration = _measurement(
        text,
        r"etch(?:ing)?\s*time|process\s*time|식각\s*(?:공정\s*)?시간",
        r"초|sec|seconds?|s\b|분|min|minutes?",
    )
    if duration:
        value, unit = duration
        minute_units = {"분", "min", "minute", "minutes"}
        physics["etch_time_sec"] = value * 60 if unit in minute_units else value
        sources["etch_time_sec"] = "user_input"
    thickness_patterns = {
        "pre_thickness_nm": r"pre[-\s]?etch\s*(?:film\s*)?thickness|식각\s*전\s*(?:막\s*)?두께",
        "post_thickness_nm": r"post[-\s]?etch\s*(?:film\s*)?thickness|식각\s*후\s*(?:막\s*)?두께",
    }
    for key, labels in thickness_patterns.items():
        measured = _measurement(text, labels, r"nm|나노미터")
        if measured:
            physics[key] = measured[0]
            sources[key] = "user_input"
    rate_patterns = {
        "target_etch_rate_nm_min": r"target\s*(?:film\s*)?etch\s*rate|목표막\s*식각\s*속도",
        "mask_etch_rate_nm_min": r"mask\s*etch\s*rate|마스크\s*식각\s*속도|보호막\s*식각\s*속도",
    }
    for key, labels in rate_patterns.items():
        measured = _measurement(text, labels, r"nm\s*/\s*min|nm/min")
        if measured:
            physics[key] = measured[0]
            sources[key] = "user_input"
    # A generic etch-rate observation is valid for the constant-rate model only
    # when it is not explicitly labelled as a target or mask rate.
    if "etch_rate_nm_min" in metrics and not any(
        physics.get(key) is not None
        for key in ("target_etch_rate_nm_min", "mask_etch_rate_nm_min")
    ):
        physics["etch_rate_nm_min"] = metrics["etch_rate_nm_min"]
        sources["etch_rate_nm_min"] = "user_input"
    physics["sources"] = sources
    data["physics"] = PhysicsInputs.model_validate(physics)

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
