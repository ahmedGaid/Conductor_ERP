# FILE_01 — PageHeaderBar primitive (sticky bar: arrows + breadcrumb + actions)

**Model:** Opus · **Est:** 30 min · **Merge checkpoint after FILE_04**

## Goal

One sticky bar at the top of every page's content area:

```
┌────────────────────────────────────────────────────────────────┐
│ ‹ ›   المبيعات › الفواتير › INV-2026-00042      [primary]  ⋯   │
└────────────────────────────────────────────────────────────────┘
```

Sticks while the page scrolls. Monochrome — this is CHROME. Pages publish their actions into it
via context (same pattern as `DocumentCrumb`); this session builds the bar + the context; rollout
to pages is FILE_02/03.

## Before You Start — read these (mandatory)

- `apps/web/src/app/AppShell.tsx` + `AppShell.css` — where the bar mounts; `page-enter` re-key
- `apps/web/src/app/RouteBreadcrumb.tsx` + css — moves INTO the bar
- `apps/web/src/app/DocumentCrumb.tsx` — the publish-per-route context pattern to copy
- `apps/web/src/components/DocumentMenu.tsx` — the ⋯ trigger/Popover to reuse as-is
- `apps/web/src/app/CommandBar.tsx` — do NOT put the arrows here; they belong to the page bar
  (decision: content-level navigation, not app chrome — revisit only if sticky layering fights)
- `apps/web/src/styles/tokens.css` — z-index/space/color tokens in use

## Tasks

1. **`PageActionsContext`** (new, in `app/`): pages publish
   `{ primary?: ReactNode; menuItems?: DocMenuItem[] }`; provider mounted per-route in AppShell
   beside `DocumentCrumbProvider` so it resets on navigation. Hook: `useSetPageActions(...)`.
2. **`components/PageHeaderBar.tsx` (+css):**
   - `position: sticky; inset-block-start: 0` inside `appshell__main`; background
     `var(--color-bg)`, `border-block-end` hairline, z-index above table headers.
   - Order (logical, so RTL just works): arrows → `RouteBreadcrumb` → spacer → primary → ⋯.
   - Renders `DocumentMenu` when `menuItems` non-empty; nothing (no dead ⋯) when empty.
3. **History arrows:** two ghost icon buttons, `navigate(-1)` / `navigate(1)`.
   - Chevrons must FLIP in RTL (back points to inline-start). Draw one chevron, flip with
     `[dir="rtl"] … transform: scaleX(-1)` or logical-aware SVG — verify visually in BOTH dirs.
   - Disabled state: back dims when `window.history.state?.idx === 0` (react-router publishes
     `idx`); forward dims when `idx` equals the max idx seen this session (track in
     sessionStorage on location change). Heuristic is fine — browsers don't expose forward.
   - Tooltips with labels; keys `shell.back` / `shell.forward` in ar+en.
4. **Move `RouteBreadcrumb` render** from `AppShell` content into the bar. Non-module routes
   (dashboard, settings…): breadcrumb returns null today — bar still renders (arrows + actions).
5. **Focus order:** bar comes before page heading in DOM; the existing focus-on-navigate effect
   (targets `h1, h2`) must still land on the page heading, not the bar — verify.
6. i18n keys both locales; parity gate.

## Acceptance

- Scroll a long page (general ledger): bar stays, content passes under, hairline visible.
- AR (RTL default) and EN: arrows flip sides AND directions correctly; breadcrumb order right.
- Back/forward mirror browser buttons exactly; dimmed states honest.
- Keyboard: tab reaches arrows/primary/⋯; Esc closes ⋯; focus-on-navigate still hits heading.
- Reduced motion: no new animation beyond existing `page-enter`.
- Monochrome check: NOTHING coloured in the bar (module accent may reach breadcrumb hover only,
  as today).

## Gates

`cd apps/web` → `node scripts/check-i18n-parity.mjs` + `npx tsc -b`; root →
`python scripts/gates/gate03.py`; then the conductor-brand feel checklist on one detail page.
Commit → rename `_done` → update `erp-status` → fresh session.
