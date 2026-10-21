# FAB Insight existing visual contract

## 1. Atmosphere & Identity
Preserve the existing quiet industrial investigation workspace: black
navigation, white conversation, pale gray evidence rail, white/black highlights, compact
Korean labels. This is an extraction of the shipped HTML/CSS, not a redesign.
Implemented as Vue 3 SFCs with the same global stylesheet (`src/assets/styles.css`);
no new brand or component library is added. Icons use Flaticon UIcons
(regular rounded, `@flaticon/flaticon-uicons`); the free license requires the
"Uicons by Flaticon" credit kept in the sidebar footer.

## 2. Color
Monotone: white, gray and black only. The authoritative palette is
`src/assets/styles.css :root`: ink #111111, muted #6b6b6b, line #e2e2e2,
surface #ffffff, canvas #f5f5f5, nav #111111, nav-muted #9a9a9a.
Accent tokens keep their names but are achromatic: mint #ffffff (highlight on
black nav), green #111111 / soft #f0f0f0, amber #666666 / soft #f5f5f5,
red #616161 / soft #f4f4f4, blue #535353 / soft #f5f5f5.
Literal shades are grayscale (luminance of the former colors). New states
reuse these tokens; do not introduce hues.
There is no alternate dark theme.

## 3. Typography
Retain Inter, Pretendard, Noto Sans KR, system sans fallbacks. Main titles are
19–25px, conversation text 15px with 1.65 line height. Labels, evidence and
metadata are 12–14px, never below 11px (enlarged on request for readability).

## 4. Spacing & Layout
Retain the 238px / flexible conversation / 330px desktop grid, 84px topbar,
790px message width (assistant left-aligned, user right-aligned), 980px records width, and existing 8–24px component spacing.
At 1100px the evidence rail becomes a drawer. At 720px records stack and
conversation padding reduces to 17px. A compact mobile navigation row preserves
access to controls hidden with the original sidebar.
Conversation, records, and evidence own their existing scrolling.

## 5. Components
Keep message/avatar, metric-card, cause-item/citation, evidence-item,
record-list-item, detail-status, record-cta, quick-replies, and button classes.
Server reports populate these primitives without frontend analysis.
The sidebar footer shows the signed-in user name. Account/logout controls are
also available in the topbar at mobile widths. The anonymous/loading/error login
gate uses the existing monochrome buttons, line borders and 12px corners:
one 440px-wide surface, 24px padding, 24px gaps, 25px heading and 15px body text.
It has no decoration, password input or signup; Keycloak owns the login form.
Judgement happens in chat: the latest pending prompt shows
equal-size quick replies (승인 primary black, others secondary); typed text
while awaiting judgement is sent as a revision request. Streaming replies show
a blinking caret.
Records show every server status and a timestamped message/event/review timeline.
Legacy records use the same cards but explicitly say local, unverified, readonly.
Network feedback is a persistent inline alert with an explicit retry button.
Pending mutations disable duplicate submissions. Empty and terminal states use
text, not simulated progress. Disabled document search stays labeled upcoming.

## 6. Motion & Interaction
Keep the existing .28s message rise, .18–.25s hover/drawer transitions and
highlight treatment. Progress changes only on backend status/events.
Reduced motion removes positional animation and smooth scrolling.
Suggestions fill the composer, citations reveal the evidence rail, quick
replies answer the latest pending prompt.

## 7. Depth & Surface
Retain thin line borders, 8–12px rounded cards/controls, pill badges,
and the existing 0 18px 50px rgba(24,39,31,.12) overlay shadow.
No new decorative surfaces or shadows.

## 8. Accessibility Constraints & Accepted Debt
Use real buttons, associated labels, visible focus, live status, textContent or
HTML escaping for all backend/user/legacy content. Long values wrap; hidden
sections must remain hidden despite their display layout rules.
Existing compact typography and sidebar geometry are preserved, not audited
as a new design. Parent owns real Aside desktop/mobile visual and interaction
QA; this implementation supplies Vitest contract tests.
