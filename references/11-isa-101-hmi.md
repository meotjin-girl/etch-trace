# ISA-101 고성능 HMI

> 원칙 레퍼런스 · 공정 제어 HMI 표준 (디자인 시스템 아님)

**링크** · [Going Gray: A New HMI Standard](https://control.com/technical-articles/going-gray/) · [ISA-101 HMI Compliance How-to](https://docs.tatsoft.com/display/FX/ISA-101+HMI+Compliance+How-to)

## 요약
공정 운전 화면의 정보 과부하·알람 남발 문제에 대응한 표준. 회색 위주 화면에 색은 주의가 필요한 곳에만 쓴다("Gray is Good").

## TRACE에 가져올 점
- 평상시 화면은 무채색, 색은 이상·주의 상태에만 — TRACE 색 원칙의 근거
- 첫 화면을 만들기 전에 스타일 가이드부터 정한다 (= `design.md`)
- 알람 위계: 정상 · 주의 · 이상 3단계

## 가져오지 않을 점
- 실제 장비 HMI의 그래픽 심볼·P&ID 표현 (TRACE는 조사 도구이지 운전 화면이 아님)

## 반영 위치
`design.md` → 1 원칙 · 2.1 의미 색
