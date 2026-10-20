# components — 컴포넌트 명세

컴포넌트 1개 = 마크다운 1개 (`status-badge.md`, `approval-card.md` …). 아래 템플릿을 복사해 씁니다.

```markdown
# {ComponentName}

- 목적: 이 컴포넌트가 해결하는 문제 한 문장
- 구성: 구성 요소 (아이콘 · 라벨 · 액션 …)
- 변형: size / tone / variant
- 상태: default · hover · focus · disabled · loading · error
- 사용 규칙: 언제 쓰고 언제 쓰지 않는가
- 접근성: 키보드 · 대비 · 스크린리더 라벨
- 사용 토큰: color.* · spacing.* …
- 코드 매핑: frontend/ 내 구현 위치
- 레퍼런스: R-xxx
```

TRACE 우선 컴포넌트: 채팅 메시지 · 재질문 카드 · 진행 타임라인 · 도구 호출 로그 · 근거 패널 · 보고서 카드 · 승인/수정 요청 카드 · 상태 배지 · 분류 배지 · 센서 비교 차트.
