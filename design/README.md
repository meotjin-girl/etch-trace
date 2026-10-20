# TRACE Design

TRACE(식각 공정 이상 조사 Agent)의 디자인 시스템과 레퍼런스를 관리하는 공간입니다.
코드(`frontend/`)와 분리해 **디자인 결정 → 토큰 → 컴포넌트 → 화면** 순서로 쌓습니다.

## 폴더 구조

```
design/
├─ README.md                 이 문서 (구조 · 작업 흐름 · 공통 규칙)
├─ references/               외부 레퍼런스 수집 (영감 · 벤치마크)
│  ├─ INDEX.md               레퍼런스 목록 (한 줄 = 한 레퍼런스)
│  ├─ products/              제품 단위 벤치마크  예) products/linear/
│  ├─ patterns/              UI 패턴 단위 — TRACE 핵심 화면 기준
│  │  ├─ agent-chat/         대화형 접수 · 재질문 · 스트리밍 응답
│  │  ├─ run-timeline/       에이전트 진행 단계 · 도구 호출 로그
│  │  ├─ evidence-citation/  근거 · 출처 · 인용 표시
│  │  ├─ review-approval/    검토 · 수정 요청 · 승인 흐름
│  │  ├─ signal-charts/      시계열 · z-score · 센서 비교 차트
│  │  ├─ admin-dashboard/    운영 지표 · 배정 · 부하 현황
│  │  └─ states-feedback/    상태 배지 · 빈 상태 · 로딩 · 오류
│  ├─ visual/                시각 언어 단위
│  │  ├─ color/  typography/  iconography/  layout/
│  └─ domain/                반도체 · 제조 현장 도메인 화면
│     ├─ fab-hmi/            장비 HMI · 알람 화면
│     └─ mes-fdc/            MES · FDC · 공정 모니터링 툴
├─ foundations/              디자인 시스템 기초 (토큰과 사용 규칙)
│  └─ tokens/                color · typography · spacing · radius · elevation · motion
├─ components/               컴포넌트 명세 (컴포넌트 1개 = 파일 1개)
├─ screens/                  역할별 화면 설계
│  ├─ worker/  engineer/  admin/  shared/
├─ assets/                   최종 산출 에셋
│  ├─ icons/  logo/  illustrations/
└─ decisions/                디자인 결정 기록 (DDR)
```

## 작업 흐름

1. **수집** — `references/`에 저장하고 `references/INDEX.md`에 한 줄 기록
2. **분석** — INDEX의 "참고 포인트"에 *무엇을 가져올지* 한 문장으로 적기
3. **결정** — 방향이 갈리는 선택은 `decisions/`에 DDR로 남기기
4. **정의** — 토큰(`foundations/`) → 컴포넌트(`components/`) 순으로 확정
5. **조립** — `screens/`에서 역할별 화면으로 조합

## 공통 규칙

| 항목 | 규칙 |
|---|---|
| 폴더 · 파일 이름 | 영문 소문자 kebab-case (`review-approval`, `status-badge.md`) |
| 문서 언어 | 한국어 (토큰 · 컴포넌트 이름은 영문) |
| 이미지 | `.webp` 또는 `.png`, 한 장 1MB 이하, 가로 2560px 이하 |
| 영상 · 대용량 | 레포에 넣지 않고 링크로 기록 |
| 원본 디자인 파일 | Figma 등 원본은 링크만 기록 (바이너리 커밋 금지) |
