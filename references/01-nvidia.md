# NVIDIA

> 메인 레퍼런스 · 엔지니어링 문서형 · 각진 정밀함 — **뼈대**

**링크** · [getdesign.md](https://getdesign.md/nvidia/design-md) · 원본 분석 [`design-md/nvidia/DESIGN.md`](design-md/nvidia/DESIGN.md)

## 요약
"엔지니어링 문서가 그래픽 디자인을 배운 것 같은" 시스템. 흰 종이 캔버스와 검정 챕터, 회색 구분선 위에 강조색 하나. 모든 면 2px 모서리로 "CAD 출력물 같은 정밀함". 그라데이션 · 메시 · 부드러운 그림자 없음. 카드 모서리에 작은 사각 마커.

## 핵심 토큰 (원본 분석 기준)
- `canvas #ffffff` · `surface-soft #f7f7f7` · `hairline #cccccc` · `body #1a1a1a` · `mute #757575`
- `rounded: xs 1px · sm 2px` — 모든 컨테이너 · 버튼 · 이미지가 2px
- 8px 기준 간격, 얇은 테두리 카드(그림자 없음)를 다열 격자로 쌓음

## TRACE에 가져올 점
- radius 2px 기본 — 화면 전체의 정밀한 인상
- 구분선 격자로 촘촘한 기술 정보 배치 (근거 표 · 보고서)
- 카드 모서리 사각 마커 → TRACE에서는 카드의 의미 상태 표시로 사용
- 강조색은 하나만, 모든 주요 행동에 일관되게

## 가져오지 않을 점
- NVIDIA Green `#76b900` — 채도가 너무 강해 장시간 사용 시 피로
- 독점 서체 NVIDIA-EMEA
- bold 700 위주의 강한 타이포 (TRACE는 600까지)
