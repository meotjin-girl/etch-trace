# TRACE visual contract

## 1. Atmosphere & Identity
Quiet investigation workspace from the team's Figma screens: light sidebar,
gray canvas, white cards, one purple accent, compact Korean labels.
Implemented as Vue 3 SFCs on `src/assets/trace.css`; no component library.
Icons use Flaticon UIcons (regular rounded, `@flaticon/flaticon-uicons`) through
`TraceIcon`; the free license requires the "Uicons by Flaticon" credit kept in the
sidebar footer. The Keycloak login page (`deploy/keycloak/themes/trace/`) uses
the same palette.

## 2. Color
The authoritative palette is `src/assets/trace.css :root`. Light: bg #f5f5f7,
sidebar #fbfbfc, surface #ffffff, surface-2 #f3f3f6, border #e2e2e8, text #18181b,
muted #52525b, faint #85858f, accent #6b3fd4, danger #c4314c, warn #9a5f00.
Dark follows `prefers-color-scheme` (bg #111113, surface #1e1e22, accent #a978f7,
danger #ec5a73, warn #e3a43c); dark values are approximations of the mockups.
Components use tokens only. Stage pills: 이상 탐지 danger, 조치 중 warn,
조치 완료 accent. Legacy token names (`--ink`, `--green`, …) map onto this palette.

## 3. Typography
Pretendard, IBM Plex Sans KR, Noto Sans KR, Inter, system sans fallbacks.
Page titles 24px/800, card titles 16–18px, body and metadata 12–13px,
never below 11px. Measurements use tabular numerals (`t-mono`).

## 4. Spacing & Layout
Desktop shell is a 225px sidebar plus flexible main column at a fixed viewport
height: the page never scrolls; only containers marked `t-scroll` or the
columns of `t-cols` scroll internally. Step pages use a two-column split
(content + 352px AI panel, 300px at ≤1280px). `PageHeader` carries the title and, on step pages,
a compact five-step bar on the right (이상 로그 → AI 조사 → 원인 확인 → 조치
검토 → 조치 기록). At ≤1080px the sidebar narrows to 180px, splits stack and
normal page scrolling returns; at ≤760px the sidebar becomes a top block.

## 5. Components
`t-card` (10px radius, 1px border), `t-btn` (accent outline; `block` full width;
`ghost` muted, used for back links), `t-pill` stage badge, `t-chip`, `t-field`,
`t-notice` (persistent inline error). `AlarmHeader` is one thin line: stage pill,
rule · measured / normal value, lot and KST time on the right.
Candidate, action review and action record pages keep a back link; before an
action is recorded the user can re-choose the cause.
`AiPanel` has 대화 / 센서 분석 / 문서 근거 tabs. Chat bubbles: user right in the
accent bubble, assistant left on surface-2, 14px radius with one 4px corner,
max 85% width, three-dot typing indicator, auto-scroll to the newest message.
The composer is a pill input with a round send button (Enter sends, Shift+Enter
new line, IME-safe); suggestions appear on an empty thread. Tool messages and
tool-call intermediates never appear as replies. Pending mutations disable
duplicate submissions; empty states use text, not simulated progress.

The hidden `/legacy` pages keep the previous task composer, report bubbles,
evidence rail and local read-only records, restyled through the mapped tokens
(`src/assets/styles.css`).

## 6. Motion & Interaction
Keep short (.18–.28s) hover, drawer and message transitions. Progress changes
only on backend status, thread state or run events.
Reduced motion removes positional animation and smooth scrolling.
Suggestions send their question; document links open the SOP·OCAP source.

## 7. Depth & Surface
Thin token borders, 8–10px rounded cards/controls, pill badges.
No decorative gradients or heavy shadows.

## 8. Accessibility Constraints & Accepted Debt
Use real buttons, associated labels, visible focus, live status, textContent or
HTML escaping for all backend/user/legacy content. Long values wrap; hidden
sections must remain hidden despite their display layout rules.
Existing compact typography and sidebar geometry are preserved, not audited
as a new design. Visual QA is manual; Vitest covers behavior contracts.
