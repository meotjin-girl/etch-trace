# ClickHouse

> 메인 레퍼런스 · 숫자가 주인공 — **관리자 지표**

**링크** · [getdesign.md](https://getdesign.md/clickhouse/design-md) · 원본 분석 [`design-md/clickhouse/DESIGN.md`](design-md/clickhouse/DESIGN.md)

## 요약
검정 캔버스에 전기 노랑을 "아껴서" 쓰는 고성능 DB 브랜드. 큰 통계 숫자(`stat-display`)를 노란 글자로 내세우고, 코드 · 제품 UI 조각을 다크 카드에 직접 삽입.

## 핵심 토큰 (원본 분석 기준)
- `stat-display`: 56px · 700 · line-height 1.0 · 자간 -1.5px
- `canvas #0a0a0a` · `surface-card #1a1a1a` · `hairline #2a2a2a`

## TRACE에 가져올 점
- 관리자 화면 KPI를 크게, 단위 없이 숫자 중심으로
- 제품 UI 조각을 다크 카드에 그대로 노출하는 방식

## 가져오지 않을 점
- 전기 노랑 `#faff69` — TRACE의 `caution` 의미와 충돌
