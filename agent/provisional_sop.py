"""Provisional investigation checklist, kept separate from retrieved evidence.

Replace these prompts with approved clauses returned by the RAG MCP when that
integration is ready. This module does not infer measurements or root causes.
"""

from .models import Context, InvestigationCheck


def provisional_checks(context: Context) -> list[InvestigationCheck]:
    """Return transparent prompts for pressure investigations only."""
    symptom = (context.symptom or "").casefold()
    metric_names = {name.casefold() for name in context.metrics}
    is_pressure = "pressure" in symptom or "압력" in symptom or "pressure_mtorr" in metric_names
    if not is_pressure:
        return []

    return [
        InvestigationCheck(
            title="문제 범위와 발생 시점 확인",
            rationale="알람 시각, Lot/Wafer, Chamber 사용 Run과 직전 Run의 추이를 대조합니다.",
        ),
        InvestigationCheck(
            title="동일 Recipe·Step의 과거 Run과 비교",
            rationale="Recipe와 Step 전환에 따른 정상 변화를 분리해 비교 조건을 맞춥니다.",
        ),
        InvestigationCheck(
            title="연관 센서의 동시 변화 확인",
            rationale="Gas Flow, 진공 펌프, 밸브 상태 및 압력 센서 신호를 함께 확인합니다.",
        ),
        InvestigationCheck(
            title="최근 정비·설정 변경 이력 확인",
            rationale="PM, 부품 교체, Chamber Cleaning, 설정 변경의 시점을 대조하되 인과관계로 단정하지 않습니다.",
        ),
        InvestigationCheck(
            title="가설별 추가 현장 점검 정리",
            rationale="배기 계통, 가스 공급·제어, 압력 센서, 운전 조건을 확인할 후보로 두고 원인은 현장에서 판단합니다.",
        ),
    ]
