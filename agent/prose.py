"""Optional constrained model prose; measurements never enter model output."""

import json
import logging
import os
from typing import Literal
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from .models import Context, Model


class Opening(Model):
    text: Literal[
        "과거 사례를 바탕으로 현장 확인이 필요한 가설을 정리했습니다.",
        "원인을 확정하지 않고 관련 사례와 문서 근거를 먼저 검토합니다.",
        "검토 의견을 기록하고 기존 근거를 유지한 확인 가설입니다.",
    ]


def model_opening(context: Context, feedback: list[str]) -> str | None:
    """Let an explicitly enabled model select safe prose, never invent facts."""
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not key or not model:
        return None
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "Select the most suitable Korean uncertainty statement from the schema. "
                    "You cannot add facts, causes, measurements or calculations."
                )},
                {"role": "user", "content": json.dumps({
                    "symptom": context.symptom, "feedback": feedback,
                }, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "opening", "strict": True, "schema": Opening.model_json_schema(),
            }},
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        return Opening.model_validate_json(result["choices"][0]["message"]["content"]).text
    except (URLError, TimeoutError, ValueError, KeyError, IndexError, ValidationError):
        logging.getLogger(__name__).warning("Optional model prose unavailable; using template")
        return None
