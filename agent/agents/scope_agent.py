"""Independent scope-agent graph backed by Business MCP cases and approved history."""

from collections.abc import Mapping
from typing import Any, cast

from ..evidence import EvidenceProvider, HistoryEvidenceReader
from ..models import Context, HistoryEvidence, InvestigationStage, Requester
from .common import AgentState, create_specialist_agent


def _history_score(record: Mapping[str, Any], context: Context) -> int:
    report = record.get("report")
    if not isinstance(report, Mapping):
        return 0
    prior = report.get("context")
    if not isinstance(prior, Mapping):
        return 0

    score = 0
    for field, points in (("equipment", 4), ("chamber", 2), ("recipe", 2)):
        requested = getattr(context, field)
        observed = prior.get(field)
        if requested and observed and str(requested).casefold() == str(observed).casefold():
            score += points

    requested_terms = {
        token.casefold()
        for token in (context.symptom or "").replace("/", " ").split()
        if len(token) > 1
    }
    historical = " ".join((
        str(record.get("question", "")),
        str(prior.get("symptom", "")),
        str(report.get("summary", "")),
    )).casefold()
    score += min(2, sum(term in historical for term in requested_terms))
    return score


def _as_history_evidence(record: Mapping[str, Any]) -> HistoryEvidence | None:
    report = record.get("report")
    if not isinstance(report, Mapping):
        return None
    cause_cases = report.get("causeCases", [])
    causes = [
        str(item.get("cause"))
        for item in cause_cases
        if isinstance(item, Mapping) and item.get("cause")
    ] if isinstance(cause_cases, list) else []
    doc_ids = report.get("docIds", [])
    return HistoryEvidence.model_validate({
        "id": str(record["id"]),
        "question": str(record.get("question", "")),
        "summary": str(report.get("summary", "")),
        "causes": causes,
        "docIds": [str(item) for item in doc_ids] if isinstance(doc_ids, list) else [],
        "approvedBy": str(record.get("approved_by", "")),
        "approvedAt": str(record.get("approved_at", "")),
        "eventTime": str(record["event_time"]) if record.get("event_time") else None,
        "lotId": str(record["lot_id"]) if record.get("lot_id") else None,
    })


def build(evidence: EvidenceProvider):
    def collect(state: AgentState) -> dict[str, object]:
        context = state["context"]
        cases = evidence.search_cases(context)
        requester: Requester | None = state.get("requester")
        history_reader = cast(
            HistoryEvidenceReader | None,
            evidence if callable(getattr(evidence, "list_investigations", None)) else None,
        )
        if requester is None or history_reader is None:
            return {"cases": cases, "history": []}

        visible_records = history_reader.list_investigations(requester)
        ranked = sorted(
            (
                (_history_score(record, context), record)
                for record in visible_records
                if isinstance(record, Mapping)
            ),
            key=lambda pair: pair[0], reverse=True,
        )
        history = [
            item
            for score, record in ranked
            if score > 0 and (item := _as_history_evidence(record)) is not None
        ][:3]
        return {"cases": cases, "history": history}

    def fallback(state: AgentState) -> InvestigationStage:
        context = state["context"]
        cases = state.get("cases", [])
        history = state.get("history", [])
        fields = [
            f"{label}={value}"
            for label, value in (
                ("장비", context.equipment), ("Chamber", context.chamber),
                ("Recipe", context.recipe), ("이상 현상", context.symptom),
            )
            if value
        ]
        findings = [
            "질문에서 추출한 범위: " + (", ".join(fields) or "미제공"),
            f"Business MCP 데모 유사 사례 {len(cases)}건을 확인했습니다.",
        ]
        if history:
            findings.append(
                f"요청자에게 조회 권한이 있는 유사 승인 조사 이력 {len(history)}건을 "
                "추가 확인했습니다."
            )
        unknowns = [
            "실제 MES Lot/Wafer, 발생 시각, Run 순서, 같은 기간의 타 Lot 사용 "
            "이력은 아직 연결되지 않았습니다."
        ]
        if not history:
            unknowns.append(
                "요청자에게 보이는 유사 승인 조사 이력이 없거나 일치하는 범위가 없습니다."
            )
        return InvestigationStage(
            key="scope", title="범위 조사 에이전트", status="sample_based",
            findings=findings,
            unknowns=unknowns,
            caseIds=[case.id for case in cases],
            historyIds=[item.id for item in history],
        )

    return create_specialist_agent(
        title="범위 조사 에이전트", status="sample_based",
        instructions=(
            "질문 범위와 Business MCP의 데모 유사 사례 및 권한 필터된 승인 이력만 근거로 "
            "정리합니다. 과거 승인도 현재 원인 확정이 아닙니다. "
            "실제 MES 조회로 오해하지 않게 하세요."
        ),
        collect=collect, fallback=fallback,
    )
