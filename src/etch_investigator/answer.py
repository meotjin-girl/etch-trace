from __future__ import annotations

from .models import ComparableCase, EvidenceLink, InvestigationRequest, MetricAnalysis


def render_answer(
    request: InvestigationRequest,
    comparables: list[ComparableCase],
    analyses: list[MetricAnalysis],
    evidence: list[EvidenceLink],
) -> str:
    context = " / ".join(
        value
        for value in [request.equipment_id, request.chamber_id, request.recipe, request.product]
        if value
    )
    lines = [
        "## 조사 답변",
        "",
        f"질문 조건: {context or '설비 범위 미지정'} / {request.symptom}",
        "",
    ]
    if not comparables:
        lines += [
            "현재 검색 조건과 비교 가능한 과거 사례를 찾지 못했습니다.",
            "장비, 챔버 또는 레시피 정보를 추가하면 검색 범위를 좁힐 수 있습니다.",
        ]
        return "\n".join(lines)

    lines += [f"관련성이 높은 과거 사례 {len(comparables)}건을 찾았습니다.", ""]
    if analyses:
        lines += ["### 수치 비교", ""]
        for item in analyses:
            pct = "계산 불가" if item.delta_pct is None else f"{item.delta_pct:+.2f}%"
            z = "계산 불가" if item.z_score is None else f"{item.z_score:+.2f}"
            lines.append(
                f"- {item.metric}: 현재 {item.current:g}, 비교군 평균 {item.baseline_mean:g}, "
                f"차이 {pct}, z-score {z} → **{item.severity}** "
                f"[{', '.join(item.supporting_case_ids)}]"
            )
        lines.append("")

    lines += ["### 우선 확인할 항목", ""]
    causes: list[tuple[str, str, str]] = []
    for item in comparables:
        if item.case.root_cause == "이상 없음":
            continue
        cause = (item.case.root_cause, item.case.action, item.case.case_id)
        if cause not in causes:
            causes.append(cause)
    for index, (cause, action, case_id) in enumerate(causes[:3], start=1):
        lines.append(f"{index}. **{cause}** — {action} [{case_id}]")

    lines += ["", "### 문서 근거", ""]
    selected_case_ids = {case_id for _, _, case_id in causes[:3]}
    relevant_evidence = [
        item for item in evidence if any(case_id in item.supports for case_id in selected_case_ids)
    ]
    if relevant_evidence:
        for item in relevant_evidence:
            lines.append(f"- [{item.evidence_id}] {item.source}: {item.excerpt}")
    else:
        lines.append("- 연결된 절차 문서를 찾지 못했습니다.")

    lines += [
        "",
        "과거 사례는 원인 후보를 좁히는 근거이며 현재 이상 원인을 확정하지 않습니다. "
        "장비 로그와 현장 점검 결과로 최종 확인해야 합니다.",
    ]
    return "\n".join(lines)

