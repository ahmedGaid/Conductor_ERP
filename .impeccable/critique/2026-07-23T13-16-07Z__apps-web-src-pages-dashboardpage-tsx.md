---
target: apps/web/src/pages/DashboardPage.tsx (Linear benchmark)
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
timestamp: 2026-07-23T13-16-07Z
slug: apps-web-src-pages-dashboardpage-tsx
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Skeleton + aria-busy present; stat-card loading vs stale not distinguished |
| 2 | Match System / Real World | 3 | Domain-correct accounting terms |
| 3 | User Control and Freedom | 2 | No in-view collapse/hide, only via Settings |
| 4 | Consistency and Standards | 3 | Raw ▲▼› Unicode glyphs break the one-icon-hand rule (confirmed live by both assessments) |
| 5 | Error Prevention | 3 | Defensive `.catch()` per cross-module fetch — page degrades gracefully on partial 403 |
| 6 | Recognition Rather Than Recall | 3 | Icons+labels paired; command palette surfaces named actions |
| 7 | Flexibility and Efficiency | 3 | Real Ctrl+K palette + "g then x" nav + shortcut sheet at shell level; doesn't reach into dashboard's own panels |
| 8 | Aesthetic and Minimalist Design | 2 | Up to 8 same-weight panels visible at once — not Linear-calm |
| 9 | Error Recovery | 3 | `ErrorState` well above bar (blame-free, retry, 403-aware) — not live-tested |
| 10 | Help and Documentation | 3 | 10 contextual Help entries confirmed live in the palette, but undiscoverable outside Ctrl+K |
| **Total** | | **28/40** | **Good** |

## Design Specificity Verdict

**LLM assessment**: Mixed, leaning generic. The custom icon set, RTL grid, and bidi-isolated numbers are authored. But the shape — 4-up KPI cards with deltas, a 2-col grid of equal-weight panels, a getting-started checklist, a records table — is the default any dashboard-builder produces; swap "EGP" for "$" and this reads as a generic Western SaaS finance dashboard. The command palette (Ctrl+K, "g then h/s/p" nav, keyboard cheat sheet) is the one place real specificity and Linear-DNA show up.

**Deterministic scan**: `detect.mjs` returned exit 0, zero findings across DashboardPage.tsx, GettingStarted.tsx, MilestoneBanner.tsx, StatCard.tsx — the automated pattern-detector has no opinion here; every substantive finding below came from direct source/DOM inspection, not the CLI tool. No false positives to flag since there were no CLI findings.

**Visual overlays**: Not available. `computer{screenshot}`/`zoom` time out on this app (documented pane-compositing issue, not something either assessment could fix), and live-server.mjs overlay injection was skipped as pointless once screenshots were confirmed dead. Both assessments instead used `read_page` (accessibility tree) and `get_page_text` against the live, authenticated dashboard with real seeded data — this is real DOM/ARIA evidence, not a guess, just not a pixel-level view. No visible browser overlay exists for this run.

## Overall Impression

The shell (nav, command palette, keyboard system, monochrome chrome) is genuinely Linear-grade — better than most ERPs ever attempt. The dashboard *body* isn't: it's a wall of 6-8 equal-weight panels with no dominant focal point, its one urgent number (negative cash balance) sends mixed signals (calm copy, alarm-red visuals), and it leaks raw Unicode glyphs into a codebase that already has a disciplined icon system to replace them with. Both independent assessments converged on the same two concrete defects (the glyph inconsistency, the unlabelled/color-only stat-card trend) without seeing each other's work — that agreement is a strong signal these are real, not one reviewer's pet peeve.

## What's Working

1. **Defensive multi-module loading** — every cross-module fetch (Sales/Purchasing/CRM/Notifications) is independently `.catch()`-guarded in `loadDashboard`, so a role without access to one module quietly empties that section instead of breaking the page. Real architectural UX discipline, confirmed in source.
2. **Designed states as a system** — `ErrorState` (blame-free, retry, distinct 403 variant) and `ListSkeleton` are shared, documented components, not per-page hacks. Matches the brand charter's own stated rule.
3. **Real keyboard-first infrastructure** — confirmed live: Ctrl+K palette with grouped Create/Go-to/Help sections, multi-key nav ("g h", "g s"...), a dedicated shortcut cheat-sheet, and 10 contextual Help entries. Most ERPs never build this; it's genuinely close to Linear's own palette.

## Priority Issues

**[P1] Foreign glyphs break the "one icon hand" brand rule** — confirmed independently by both assessments.
- Location: `StatCard.tsx:40` (`▲`/`▼` for trend direction), `DashboardPage.tsx` (bare `›` chevron, 3 places: attention rows, shortcut rows; bare `+` on shortcut icons), `MilestoneBanner.tsx:89` (`›`)
- Why it matters: CLAUDE.md mandates "one icon hand... no third font, no imported icon library" — this is a literal violation sitting next to a disciplined custom `NavIcon` set that already has matching names (`trendUp`/`trendDown` etc. exist). Linear never mixes bespoke icons with raw Unicode.
- Fix: swap all of the above to `<NavIcon>` components; add a `chevronEnd` icon if none exists for `›`.
- Suggested command: `/impeccable polish`

**[P1] Stat-card trend is color/icon-only for assistive tech**
- Location: `StatCard.tsx:40` — direction glyph is `aria-hidden="true"`, delta text is `Math.abs()`'d, so a screen reader announces only the bare percentage with no up/down word. Confirmed live: the four label/value/delta/hint pieces render as unconnected sibling `generic` nodes with no `role="group"`/`aria-label` tying them together.
- Why it matters: violates the app's own accessibility ambition and Nielsen #1 for an entire user class — a screen-reader user cannot tell whether 176.2% is good or bad news.
- Fix: wrap each StatCard root in `role="group" aria-label="{label}: {value}, {delta}% {trendWord} vs last month"`; give the arrow a sr-only text equivalent.
- Suggested command: `/impeccable harden`

**[P2] Negative cash balance: calm copy, alarming visuals, zero context**
- Location: Cash Balance KPI card, live-confirmed value `-1,377,222.68 EGP` with "Balance is negative" hint, large red bold number + warning-triangle icon.
- Why it matters: highest-stakes number on the page for an SMB owner; copy and visual register disagree (blame-free wording, five-alarm-fire styling), and nothing explains the cause or links to a next action.
- Fix: either tone the color down one step and make the hint an actionable link to Cash Flow, or commit the visual register to match the copy's calm — pick one, don't run both.
- Suggested command: `/impeccable clarify`

**[P2] No single dominant focal point — up to 8 equal-weight panels visible at once**
- Location: full dashboard body (4 KPI cards + Needs-attention + System-confidence + Top-Expenses + Cash-Flow + Recent-Journals + Shortcuts).
- Why it matters: directly contradicts the stated Linear benchmark ("information density done calmly"); cognitive-load checklist fails on single-focus, hierarchy, one-thing-at-a-time, and progressive-disclosure.
- Fix: collapse "System confidence" to a compact always-ok strip that expands only when something needs attention; combine Top-Expenses/Cash-Flow/Recent-Journals into one tabbed panel instead of 3 parallel cards.
- Suggested command: `/impeccable distill`

**[P3] Duplicate closing-balance number with no cross-reference**
- Location: Cash Balance KPI (`-1,377,222.68 EGP`) and Cash Flow panel's "Closing balance" row show the identical figure with no visual link between them.
- Why it matters: forces the user to reconcile the two panels themselves instead of the UI doing it.
- Fix: make the KPI card's hint a link/anchor straight to the Cash Flow panel.
- Suggested command: `/impeccable layout`

## Persona Red Flags

**Alex (Power User)**: The app has a fully-built list-keyboard-nav vocabulary (confirmed live in the shortcuts overlay's "Lists" section: Next/Previous row, Open row, Peek) — but the dashboard's own attention/confidence lists don't participate in it, so Alex must reach for the mouse to act on "2 purchase orders awaiting approval" despite the infrastructure already existing elsewhere in the app. No in-view panel collapse either — decluttering requires a trip to Settings.

**Sam (Accessibility)**: Stat cards read to a screen reader as four disconnected fragments ("Total Revenue" / "39,915.00 EGP" / "176.2%" / "vs last month") with no relationship and no trend direction — the ▲/▼ is `aria-hidden`, so Sam cannot tell whether any given percentage is good or bad news at all. Confirmed via live accessibility-tree read, not inferred from source alone.

## Minor Observations

- `RecentJournals` table has no `<thead>` — columns (number/memo/date/amount) are guessable but unlabelled for a data table.
- Heading hierarchy is correct (single h1 → 6 h2 sections, no skipped levels) — confirmed live, worth noting as a pass.
- Command palette's 10-entry Help section is excellent but only discoverable via Ctrl+K — a non-keyboard or first-time user may never find it.
- `MilestoneBanner` dismiss is fire-and-forget with an in-code comment acknowledging it may silently reappear on failure — reasonable trade-off, not a bug.
- A native `<dialog>` (ShortcutsDialog) surfaced its full content in one tool's DOM snapshot even though never opened this session — flagged by Assessment B as a likely tool/snapshot artifact (walks DOM rather than true AX tree), not an app bug.

## Questions to Consider

- If "quiet, precise, trustworthy" is the brand and Linear is the bar, why does the single highest-stakes number on the page (negative cash) get the loudest visual treatment instead of the calmest?
- The app has Linear-grade keyboard infrastructure at the shell level — why does none of it reach into the dashboard's own panels yet?
- `dashboardWidgets.ts` already treats panels as an ordered, hideable registry — is the current default order (4 KPIs first, Needs-attention buried below) the one an Egyptian SMB owner would actually choose each morning, or just the one that was easiest to build first?
