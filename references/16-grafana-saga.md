# Grafana Saga

> 원칙 레퍼런스 · 모니터링 플랫폼 오픈소스 디자인 시스템

**링크** · [Saga 개요](https://grafana.com/developers/saga/about/overview/) · [소개 블로그](https://grafana.com/blog/2023/11/07/saga-design-system-shaping-the-future-of-user-experiences-at-grafana-labs)

## 요약
Grafana Labs 제품 전체의 시각 언어. Foundations · Components · Patterns와 Figma 라이브러리, `@grafana/ui` Storybook 제공.

## TRACE에 가져올 점
- 시계열 패널 구성 (센서 추세 · 관리자 지표)
- 모니터링 화면의 다크 테마 사용 맥락

## 가져오지 않을 점
- 다색 계열 차트 팔레트 (TRACE는 회색 + 강조 1색)

## 반영 위치
`design.md` → 4 화면 적용 (관리자) · 3 Components (차트)
