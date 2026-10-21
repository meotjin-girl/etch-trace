# FAB Insight existing visual contract

## 1. Atmosphere & Identity
Preserve the existing quiet industrial investigation workspace: dark forest
navigation, white conversation, pale evidence rail, mint highlights, compact
Korean labels. This is an extraction of the shipped HTML/CSS, not a redesign.
No framework, font download, new brand, or component library is required.

## 2. Color
The authoritative palette remains `styles.css :root`: ink #17211d, muted #66736c,
line #dfe5e1, surface #ffffff, canvas #f4f6f3, nav #15231d, nav-muted #94a39b,
mint #b9f3d1, green #18794e / soft #eaf8ef, amber #9a5b13 / soft #fff5df,
red #b93b3b / soft #fff0ef, blue #245d9b / soft #eef6ff.
Existing literal surface shades remain unchanged. New states reuse these tokens.
There is no alternate dark theme.

## 3. Typography
Retain Inter, Pretendard, Noto Sans KR, system sans fallbacks. Main titles are
19–25px, conversation text 14px with 1.65 line height, compact labels 9–12px.
Existing small evidence and metadata type is preserved by explicit request.

## 4. Spacing & Layout
Retain the 238px / flexible conversation / 330px desktop grid, 84px topbar,
790px message width, 980px records width, and existing 8–24px component spacing.
At 1100px the evidence rail becomes a drawer. At 720px records stack and
conversation padding reduces to 17px. A compact mobile navigation row preserves
access to controls hidden with the original sidebar. Identity controls wrap.
Conversation, records, dialog preview, and evidence own their existing scrolling.

## 5. Components
Keep message/avatar, metric-card, cause-item/citation, evidence-item,
record-list-item, detail-status, record-cta, report-dialog, and button classes.
Server reports populate these primitives without frontend analysis.
Session controls display the parsed token name, login/logout, loading, and an
inline authentication error with retry using the existing secondary buttons.
The authentication group reserves a 44px control row during loading. Its buttons
have 44px minimum targets, green-soft hover and mint pressed feedback, with the
existing focus ring. The login action names Keycloak and disables duplicate
redirects while its inline status announces navigation.
Unauthenticated workspace regions are inert and hidden from interaction.
Review uses readonly actor,
optional occurrence time/Lot ID, comment, approve/revise, and non-submit close.
Records show every server status and a timestamped message/event/review timeline.
Legacy records use the same cards but explicitly say local, unverified, readonly.
Network feedback is a persistent inline alert with an explicit retry button.
Pending mutations disable duplicate submissions. Empty and terminal states use
text, not simulated progress. Disabled document search stays labeled upcoming.

## 6. Motion & Interaction
Keep the existing .28s message rise, .18–.25s hover/drawer transitions and
highlight treatment. Progress changes only on backend status/events.
Reduced motion removes positional animation and smooth scrolling.
Suggestions fill the composer, citations reveal the evidence rail, native
dialog supplies keyboard focus trapping and Escape close.

## 7. Depth & Surface
Retain thin line borders, 8–12px rounded cards/controls, 15px dialog, pill badges,
and the existing 0 18px 50px rgba(24,39,31,.12) overlay shadow.
No new decorative surfaces or shadows.

## 8. Accessibility Constraints & Accepted Debt
Use real buttons, associated labels, visible focus, live status, textContent or
HTML escaping for all backend/user/legacy content. Long values wrap; hidden
sections must remain hidden despite their display layout rules.
Existing compact typography and sidebar geometry are preserved, not audited
as a new design. Parent owns real Aside desktop/mobile visual and interaction
QA; this implementation supplies dependency-free contract tests.
