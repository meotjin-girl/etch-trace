from __future__ import annotations

from statistics import fmean, pstdev

from .models import ComparableCase, InvestigationRequest, MetricAnalysis


def analyze_metrics(
    request: InvestigationRequest, comparables: list[ComparableCase]
) -> list[MetricAnalysis]:
    results: list[MetricAnalysis] = []
    for metric, current in request.metrics.items():
        observations = [
            (item.case.case_id, item.case.metrics[metric])
            for item in comparables
            if metric in item.case.metrics
        ]
        if not observations:
            continue
        values = [value for _, value in observations]
        mean = fmean(values)
        std = pstdev(values) if len(values) > 1 else 0.0
        delta = current - mean
        delta_pct = (delta / mean * 100) if mean else None
        z_score = (delta / std) if std else None
        absolute_z = abs(z_score) if z_score is not None else 0.0
        absolute_pct = abs(delta_pct) if delta_pct is not None else 0.0
        if absolute_z >= 2.0 or absolute_pct >= 20.0:
            severity = "abnormal"
        elif absolute_z >= 1.0 or absolute_pct >= 10.0:
            severity = "watch"
        else:
            severity = "normal"
        results.append(
            MetricAnalysis(
                metric=metric,
                current=current,
                baseline_mean=round(mean, 4),
                baseline_std=round(std, 4),
                delta=round(delta, 4),
                delta_pct=round(delta_pct, 2) if delta_pct is not None else None,
                z_score=round(z_score, 2) if z_score is not None else None,
                severity=severity,
                supporting_case_ids=[case_id for case_id, _ in observations],
            )
        )
    return results

