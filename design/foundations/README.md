# foundations — 디자인 토큰

모든 화면 값은 토큰으로만 참조합니다. 토큰 원본은 `tokens/`에 두고, 각 토큰의 사용 규칙은 같은 폴더의 문서에 적습니다.

| 분류 | 파일 (예시) | 담을 내용 |
|---|---|---|
| Color | `tokens/color.json` · `color.md` | 기본 팔레트, 의미 색 (상태 · 분류 · 심각도), 다크 모드 |
| Typography | `tokens/typography.json` · `typography.md` | 글꼴, 크기 단계, 줄 간격, 숫자 · 코드 표기 |
| Spacing | `tokens/spacing.json` | 간격 단계 (4px 기준 등) |
| Radius · Elevation | `tokens/radius.json` · `tokens/elevation.json` | 모서리, 그림자 단계 |
| Motion | `tokens/motion.json` | 진행 · 스트리밍 표시의 시간 · 곡선 |

TRACE에서 특히 정해야 할 의미 색: 작업 상태(`QUEUED`~`FAILED`), 분류(장비 · 공정 · 불명확), 편차 강도(|z| 2~3 · ≥3), 사람 입력 대기(interrupt).
