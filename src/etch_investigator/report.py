from __future__ import annotations

from datetime import datetime, timezone

from .models import ComparableCase, EvidenceLink, InvestigationRequest, MetricAnalysis


def render_report(
    request: InvestigationRequest,
    comparables: list[ComparableCase],
    analyses: list[MetricAnalysis],
    evidence: list[EvidenceLink],
    review_notes: list[str] | None = None,
) -> str:
    abnormal = [item for item in analyses if item.severity == "abnormal"]
    watch = [item for item in analyses if item.severity == "watch"]
    leading_causes: list[str] = []
    for item in comparables[:3]:
        cause = item.case.root_cause
        if cause != "이상 없음" and cause not in leading_causes:
            leading_causes.append(cause)

    lines = [
        "# 식각 장비 이상 조사 기록",
        "",
        f"- 기록 생성(UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 장비 / 챔버: {request.equipment_id} / {request.chamber_id}",
        f"- 발생 시각: {request.event_time}",
        f"- Lot / 제품 / 레시피: {request.lot_id or '미제공'} / {request.product or '미제공'} / {request.recipe}",
        f"- 현상: {request.symptom}",
        "",
        "## 1. 판정 요약",
        "",
        f"- 비정상 지표 {len(abnormal)}개, 주의 지표 {len(watch)}개",
        "- 과거 사례에서 관찰된 우선 확인 가설: "
        + (", ".join(leading_causes) if leading_causes else "근거 부족"),
        "- 아래 원인 후보는 유사 사례와의 연관성이며 인과 확정이 아니다. 현장 점검과 추가 계측으로 확인해야 한다.",
        "",
        "## 2. 수치 분석",
        "",
        "| 지표 | 현재값 | 비교군 평균 | 표준편차 | 차이(%) | z-score | 판정 | 근거 사례 |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    if analyses:
        for item in analyses:
            pct = "N/A" if item.delta_pct is None else f"{item.delta_pct:.2f}%"
            z = "N/A" if item.z_score is None else f"{item.z_score:.2f}"
            lines.append(
                f"| {item.metric} | {item.current:.4g} | {item.baseline_mean:.4g} | "
                f"{item.baseline_std:.4g} | {pct} | {z} | {item.severity} | "
                f"{', '.join(item.supporting_case_ids)} |"
            )
    else:
        lines.append("| - | - | - | - | - | - | 분석 불가 | 비교 가능한 계측값 없음 |")

    lines += [
        "",
        "## 3. 비교 사례",
        "",
        "| 사례 | 유사도 | 비교 근거 | 당시 원인 | 조치 |",
        "|---|---:|---|---|---|",
    ]
    for item in comparables:
        lines.append(
            f"| {item.case.case_id} | {item.similarity:.3f} | {', '.join(item.match_reasons)} | "
            f"{item.case.root_cause} | {item.case.action} |"
        )

    lines += ["", "## 4. 문서 근거 연결", ""]
    for item in evidence:
        lines.append(f"- [{item.evidence_id}] **{item.source}** — {item.excerpt} → {item.supports}")

    lines += [
        "",
        "## 5. 권고 조사 순서",
        "",
        "1. 장비 로그 원본과 계측 시각 동기화 여부를 보존·확인한다.",
        "2. 비정상 지표와 직접 연관된 소모품·가스계·RF 계통을 우선 점검한다.",
        "3. 동일 레시피의 정상 wafer와 재현 시험을 수행하고 전후 계측값을 기록한다.",
        "4. 가설별 확인 결과를 증거 ID와 함께 추가한 뒤 원인을 확정한다.",
        "",
        "## 6. 승인 체크",
        "",
        f"- [x] 필수 식별정보 충족",
        f"- [{'x' if comparables else ' '}] 비교 가능한 과거 사례 포함",
        f"- [{'x' if analyses else ' '}] 수치 분석과 원천 사례 연결",
        f"- [{'x' if evidence else ' '}] 절차/기준 문서 연결",
        "- [ ] 조사 책임자 검토 및 승인",
    ]
    if review_notes:
        lines += ["", "## 검토 이력", ""] + [f"- {note}" for note in review_notes]
    return "\n".join(lines) + "\n"

