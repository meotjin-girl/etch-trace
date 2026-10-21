"""Shared runtime for five separately compiled specialist-agent subgraphs."""

import json
import logging
import os
from collections.abc import Callable
from typing import TypedDict
from urllib.error import URLError
from urllib.request import Request, urlopen

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError

from ..models import (
    Case,
    Context,
    Document,
    HistoryEvidence,
    InvestigationCheck,
    InvestigationStage,
    Metric,
    Requester,
)


class AgentState(TypedDict, total=False):
    requester: Requester | None
    context: Context
    cases: list[Case]
    metrics: list[Metric]
    documents: list[Document]
    history: list[HistoryEvidence]
    checks: list[InvestigationCheck]
    sop_search_error: str | None
    sensor_data: list[dict[str, object]]
    maintenance_records: list[dict[str, object]]
    stages: list[InvestigationStage]
    result: InvestigationStage


class AgentDraft(BaseModel):
    """LLM may phrase findings, but IDs/status remain code-owned."""
    findings: list[str]
    unknowns: list[str]


type Collect = Callable[[AgentState], dict[str, object]]
type Fallback = Callable[[AgentState], InvestigationStage]
type Status = str | Callable[[AgentState], str]


def _jsonable(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _ask_model(role: str, instructions: str, state: AgentState) -> AgentDraft | None:
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
                    f"당신은 반도체 식각 이상 조사에서 '{role}' 역할을 맡은 전문 에이전트입니다. "
                    f"{instructions} 입력 JSON에 있는 근거만 사용하세요. 연결되지 않은 MES, "
                    "센서, 정비 이력을 조회했다고 말하지 마세요. SOP는 입력 JSON에 실제 "
                    "검색 결과가 포함된 경우에만 해당 조항을 인용하세요. "
                    "관측 사실과 가설을 구분하세요. 사례/문서 ID를 보존하고 "
                    "근거가 부족하면 명시하세요. 계측값, 원인, 조치를 만들어내지 마세요. "
                    "간결한 한국어 findings와 unknowns를 반환하세요."
                )},
                {"role": "user", "content": json.dumps(_jsonable({
                    key: value for key, value in state.items() if key != "requester"
                }), ensure_ascii=False)},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "specialist_result", "strict": True,
                "schema": AgentDraft.model_json_schema(),
            }},
        }, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.load(response)
        return AgentDraft.model_validate_json(payload["choices"][0]["message"]["content"])
    except (URLError, TimeoutError, ValueError, KeyError, IndexError, ValidationError):
        logging.getLogger(__name__).warning(
            "Specialist %s model call failed; deterministic result will be used", role,
        )
        return None


def create_specialist_agent(
    *,
    title: str,
    status: Status,
    instructions: str,
    collect: Collect,
    fallback: Fallback,
):
    """Compile one independently invokable LangGraph specialist subgraph."""

    def gather(state: AgentState) -> dict[str, object]:
        return collect(state)

    def reason(state: AgentState) -> dict[str, InvestigationStage]:
        deterministic = fallback(state)
        draft = _ask_model(title, instructions, state)
        if draft is None:
            result = deterministic.model_copy(update={"agent_mode": "rule_based"})
        else:
            stage_status = status(state) if callable(status) else status
            result = deterministic.model_copy(update={
                "status": stage_status,
                "findings": list(dict.fromkeys([
                    *deterministic.findings, *draft.findings,
                ])),
                "unknowns": list(dict.fromkeys([*deterministic.unknowns, *draft.unknowns])),
                "agent_mode": "llm",
            })
        return {"result": result}

    builder = StateGraph(AgentState)
    builder.add_node("collect_evidence", gather)
    builder.add_node("specialist_reasoning", reason)
    builder.add_edge(START, "collect_evidence")
    builder.add_edge("collect_evidence", "specialist_reasoning")
    builder.add_edge("specialist_reasoning", END)
    return builder.compile()
