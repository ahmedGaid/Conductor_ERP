# Conductor ERP – Product Design & Engineering Directive

> Status: **active design charter.** This is the standing UI/UX contract for Conductor. Every new
> screen, component, and state must satisfy it; gate03 enforces the mechanical parts (tokens-only
> colour, logical-CSS only, i18n ar/en parity, clean build). The rest is reviewed on sight.

## Vision

Build Conductor ERP as the **"Telegram of ERP Systems."**

The goal is not to replicate Telegram's features, but to adopt its **clarity, speed, simplicity,
readability, and confidence.**

Every screen should feel modern, lightweight, responsive, and focused. The user should never feel
overwhelmed by the system, even when using advanced ERP functionality.

## What "Telegram of ERP" means, concretely

Translating the five qualities above into rules we can actually build and check against:

### 1. Clarity — one obvious thing per screen
- Each screen has a **single primary job** and one primary action. Secondary actions are visibly
  secondary (ghost/sm buttons), never competing for the eye.
- A consistent page header: `page-title` + optional `page-subtitle` + a right-aligned primary action.
- Money, codes, dates, and statuses are always rendered the same way (status pills, `tabular-nums`,
  `<Bdi>` for LTR tokens inside Arabic) so the user learns the language once.
- No raw jargon without a human label; errors say what happened and what to do next.

### 2. Speed — it must feel instant
- One **motion scale** only: `--dur-fast` (120ms) / `--dur` (180ms) / `--dur-slow` (260ms) with
  `--ease-out`. Interactions are snappy and uniform; nothing janks or lingers.
- Optimistic, immediate feedback on every action (pressed state, disabled-while-pending, inline
  result). Never leave the user wondering if a click registered.
- Loading is **never a blank screen**: show skeletons/placeholders that match the final layout, so the
  page doesn't reflow when data lands.
- Respect `prefers-reduced-motion` — motion is polish, never a barrier.

### 3. Simplicity — remove before you add
- Default to the **lightest control** that works: a link over a button, a segmented control over a
  dropdown, inline edit over a modal. Reach for a modal only when focus must be trapped.
- Progressive disclosure: advanced/rare ERP options are tucked behind "more"/detail views, not on the
  first screen. The 80% path is front and centre.
- Calm surfaces: thin `--color-border` dividers and `--shadow-xs/sm`, not heavy boxes and drop
  shadows. Whitespace (the `--space-*` scale) does the grouping.

### 4. Readability — built for long workdays
- Generous line-height (`--line-height-ui`), comfortable density, and a strict type scale. Numbers use
  `font-variant-numeric: tabular-nums` so columns align.
- Strong text/background contrast (WCAG AA min); never communicate by colour alone — pair every status
  colour with a word or icon.
- Tables: muted, medium-weight headers; right-aligned (logical `end`) numeric columns; quiet row
  hover; bold totals separated by a rule. Horizontal scroll only inside the table, never the page.

### 5. Confidence — the system feels solid and trustworthy
- Destructive or irreversible actions confirm and are visually distinct (`btn--danger`).
- Every empty state is **designed** (what this is, why it's empty, the one action to fill it) — never a
  bare "No data."
- Consistent, keyboard-reachable focus: one `:focus-visible` ring (`--focus-ring`) across the whole
  app; full keyboard operability; visible focus order.
- Errors are caught and shown inline near their cause, in the user's language, with ar/en parity.

## Non-negotiable engineering rules (enforced by gates)
- **Colour:** only `tokens.css` may contain raw hex. Everything else uses `var(--color-*)`. (gate03)
- **Direction:** Arabic/RTL is the default. **Logical CSS only** — `inline-start/end`, `block-*`,
  `text-align: start/end`; no physical `left/right`. (gate03)
- **i18n:** every user-facing string is a key with **ar + en parity**; the build fails on drift. (gate03)
- **Money:** integer minor units on the wire; format/parse only at the edge (`lib/money.ts`).
- **One source of truth for design:** spacing, radii, type, elevation, **and motion** are tokens. No
  magic numbers in component CSS where a token exists.

## Design tokens that encode this (`src/styles/tokens.css`)
- Palette → semantic colour (near-black **Conductor** brand; blue accent; success/warning/danger/info;
  a full status-colour map).
- `--space-*` rhythm, `--radius-*`, the type scale + weights, `--shadow-xs…lg` elevation.
- **Motion:** `--ease-out`, `--ease-in-out`, `--dur-fast|--dur|--dur-slow`.
- **Focus:** `--focus-ring` (brand-tinted keyboard ring).

## Implementation log
- **2026-06-16 — Charter adopted + system tightened to it.** Added the motion + focus-ring token scale;
  applied one app-wide `:focus-visible` discipline; on-brand `::selection`; a `prefers-reduced-motion`
  guard; standardized button/input/link/nav transitions onto the motion scale; gave dashboard KPI cards
  a calm hover lift. No colour-identity change (near-black brand kept). gate03 (build + token/logical-CSS
  scans + i18n parity) green.
- **2026-06-16 — Navigation feel: motion tuned + perceived latency removed.** Page transition cut to a
  fast, GPU-only fade (`--dur`, 2px rise, resolves to `transform: none`); removed the KPI-card hover
  lift in favour of a crisp 120ms shadow. **Loading flash eliminated app-wide:** `useAsync` gained an
  optional `cacheKey` (stale-while-revalidate via `lib/cache.ts`) so revisited pages/forms paint
  last-known data instantly and refresh in the background, and the bare "Loading…" text was replaced on
  every page with **layout-matched shimmer skeletons** for genuine cold loads. Cache keys wired across
  all list + shared reference loaders (customers/items/warehouses/accounts/etc.), so form dropdowns are
  instant on revisit too. gate03 green.
- **2026-06-16 — Mutation cache-invalidation: created records show up immediately.** `apiFetch` now
  evicts the affected cached lists after any successful write (non-GET), via a single path→keys map in
  `lib/cache.ts` (e.g. a new sales order clears `sales:orders` + `dashboard`; a stock movement clears
  `inventory:movements` + `inventory:stock-on-hand` + `accounting:journals` + `dashboard`; quotation/PR
  convert and a won opportunity also clear the spawned order list). So a created/changed record is
  always freshly refetched the next time its list is shown — never a known-stale view. Centralized, so
  future mutations are covered automatically. gate03 green.
- **Backlog (apply per screen as we touch them):** designed empty states everywhere (still bare "No
  data" lines today); per-report skeletons + caching for the filtered statement screens; a responsive
  pass for narrow/tablet widths; reduce information density on the busiest detail screens via
  progressive disclosure.
