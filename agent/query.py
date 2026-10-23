"""LLM-based Korean/English question understanding for the legacy graph path."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError

from .models import Context, PhysicsInputs


def _measurement(text: str, labels: str, units: str) -> tuple[float, str] | None:
    match = re.search(
        rf"(?:{labels})[^\d]{{0,24}}(\d+(?:\.\d+)?)\s*({units})",
        text,
        flags=re.IGNORECASE,
    )
    return (float(match.group(1)), match.group(2).lower()) if match else None


class QuestionUnderstanding(BaseModel):
    """Extract only facts the requester explicitly supplied."""

    equipment: str | None = None
    chamber: str | None = None
    recipe: str | None = None
    symptom: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


def understand_question(text: str, existing: Context | None = None) -> QuestionUnderstanding:
    """Use an LLM to extract scope, symptom and measurements without pattern matching."""
    key, model = os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_MODEL")
    if not key or not model:
        return QuestionUnderstanding(
            equipment=existing.equipment if existing else None,
            chamber=existing.chamber if existing else None,
            recipe=existing.recipe if existing else None,
            symptom=existing.symptom if existing else None,
            metrics=existing.metrics if existing else {},
        )

    prior = existing.model_dump(mode="json") if existing else Context().model_dump(mode="json")
    schema = {
        "type": "object",
        "properties": {
            "equipment": {"type": ["string", "null"]},
            "chamber": {"type": ["string", "null"]},
            "recipe": {"type": ["string", "null"]},
            "symptom": {"type": ["string", "null"]},
            "metrics": {
                "type": "object",
                "properties": {
                    key: {"type": ["number", "null"]}
                    for key in (
                        "endpoint_sec",
                        "etch_rate_nm_min",
                        "rf_reflected_w",
                        "pressure_mtorr",
                    )
                },
                "required": [
                    "endpoint_sec",
                    "etch_rate_nm_min",
                    "rf_reflected_w",
                    "pressure_mtorr",
                ],
                "additionalProperties": False,
            },
        },
        "required": ["equipment", "chamber", "recipe", "symptom", "metrics"],
        "additionalProperties": False,
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "질문을 이해해 조사 범위와 관측 사실을 JSON으로 추출하는 반도체 식각 조사 보조자입니다. "
                            "반드시 JSON schema를 정확히 따르세요. "
                            "ETCh 장비명, chamber, recipe, 관측 증상, 명시된 수치와 단위를 표준화하세요. "
                            "사용자가 실제로 말하지 않은 값은 추측하거나 생성하지 마세요. "
                            "기존 context가 있으면 새로 명시된 값만 갱신하고 언급되지 않은 값은 유지하세요. "
                            "수치는 endpoint_sec, etch_rate_nm_min, rf_reflected_w, pressure_mtorr 중 "
                            "대응하는 metric key가 명확할 때만 숫자로 반환하고, 단위가 의미를 바꾸면 "
                            "추출하지 마세요. 모호한 표현은 null/빈 metrics로 두세요."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"existing_context": prior, "new_user_message": text},
                            ensure_ascii=False,
                        ),
                    },
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "question_understanding",
                        "strict": True,
                        "schema": schema,
                    },
                },
            },
            ensure_ascii=False,
        ).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.load(response)
        extracted = json.loads(payload["choices"][0]["message"]["content"])
        extracted["metrics"] = {
            key: value for key, value in extracted.get("metrics", {}).items() if value is not None
        }
        return QuestionUnderstanding.model_validate(extracted)
    except (OSError, TimeoutError, ValueError, KeyError, IndexError, ValidationError):
        return QuestionUnderstanding.model_validate(prior)


def parse_question(text: str, existing: Context | None = None) -> Context:
    """Merge LLM-understood facts into the current typed investigation context."""
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
        questions.append("어떤 이상 현상이 관찰됐나요? 관측된 표현이나 수치를 알려주세요.")
    if "scope" in missing:
        questions.append("어느 장비·챔버·레시피에서 발생했나요? 아는 항목만 알려주세요.")
    return " ".join(questions)
