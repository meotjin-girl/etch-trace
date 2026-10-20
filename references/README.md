# References

TRACE 디자인 방향 **Quiet Instrument** — *NVIDIA의 정밀한 뼈대 + Linear · Warp의 따뜻한 다크 + xAI의 mono 라벨*, 그 위에 산업 HMI의 색 절제 원칙.

## 메인 레퍼런스 — 시각 언어
[getdesign.md](https://getdesign.md)(공개 사이트 디자인 분석 DESIGN.md 모음)에서 선정. 원본 분석 파일은 [`design-md/`](design-md/)에 보관.

| 레퍼런스 | 역할 | 가져올 것 |
|---|---|---|
| [NVIDIA](01-nvidia.md) | **뼈대** | 2px 각진 모서리, 구분선 격자, 카드 사각 마커, 강조색 하나 |
| [Linear](02-linear.md) | **다크 모드 기준** | 면 계단, 포커스 · 핵심 행동에만 강조, 눌린 내비게이션 |
| [Warp](03-warp.md) | **다크 톤** | 순흑 대신 따뜻한 차콜 |
| [xAI · SpaceX](04-xai-spacex.md) | **메타 정보** | mono 대문자 + 넓은 자간 라벨 |
| [IBM](05-ibm.md) | 표 · 타일 | 그림자 없는 타일, 회색 행 구분 |
| [ClickHouse](06-clickhouse.md) | 관리자 지표 | 큰 숫자 중심 KPI |

## 원칙 레퍼런스 — 산업 · AI · 데이터 규칙

| 레퍼런스 | 역할 |
|---|---|
| [ISA-101 고성능 HMI](11-isa-101-hmi.md) | 색은 이상 상태에만 ("Gray is Good") |
| [Siemens iX](12-siemens-ix.md) | 산업용 테마 · 상태 컴포넌트 |
| [Vercel Geist](13-vercel-geist.md) | 숫자 · ID mono 타이포 |
| [Carbon for AI](14-carbon-for-ai.md) | AI 라벨 → 근거 연결 |
| [Palantir Blueprint](15-palantir-blueprint.md) | 데이터 밀도 높은 표 · 패널 |
| [Grafana Saga](16-grafana-saga.md) | 시계열 · 모니터링 |
| [SAP 생성형 AI 가이드](17-sap-ai-guidelines.md) | 사람 검토 · 승인 |

## 규칙
- 레퍼런스 1개 = 문서 1개: 요약 · 핵심 토큰 · 가져올 점 · 가져오지 않을 점
- **구조와 규칙만** 가져오고, 브랜드 고유색 · 독점 서체는 쓰지 않는다
- 공개 저장소이므로 타사 화면 스크린샷은 넣지 않고 링크로 기록
- `design-md/`의 DESIGN.md는 공개 사이트에 대한 독립 분석이며 각 회사의 공식 문서가 아니다. 출처: [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) (MIT, [`design-md/LICENSE`](design-md/LICENSE)), 2026-10-14 커밋 `3b60532` 기준
