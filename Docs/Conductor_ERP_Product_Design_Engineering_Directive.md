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
- **2026-06-16 — Designed empty states on the primary lists.** New reusable `<EmptyState>` (quiet icon
  + headline + one line of guidance + an optional primary CTA) replaces the bare "No data" lines on the
  module landing lists: Sales orders/quotations, Purchasing orders/requests, Journals, and Workflows
  get a create-CTA that routes to their New screen; CRM (leads/tickets/pipeline) and E-invoices show
  headline + guidance (their create is inline / auto-generated). One shared `common.emptyHint` string
  (ar+en). gate03 green.
- **2026-06-16 — Responsive shell (tablet / phone).** Below 64rem the sidebar becomes an off-canvas
  **drawer** (RTL-aware slide, behind a scrim overlay) toggled by a hamburger in the command bar; the
  shell grid goes single-column, content padding tightens, and the command bar drops its placeholder
  search + non-essential icons to reclaim width. Drawer closes on navigation and on overlay tap. The
  dashboard KPI grid collapses 4→2→1 across 60rem/38rem; every module table already scrolls within its
  card, so wide tables never break the page. gate03 green (logical-CSS scan clean — the off-canvas hide
  uses a dir-flipped transform, not physical left/right).
- **Backlog (apply per screen as we touch them):** empty states on the form+table reference screens
  (customers/suppliers/items/warehouses/COA — emptiness is already self-evident there next to the add
  form); per-report skeletons + caching for the filtered statement screens; reduce information density
  on the busiest detail screens via progressive disclosure; sticky table headers on long lists.

## Reconciled UX-tips backlog (2026-06-19)

Two external UX/UI agent prompts (`Docs/conductor_erp_ai_agent_prompt ui ux tips.md` and `… tips 2.md`)
were reviewed against this charter. ~70% of their content is already built or already stated here; they
are **not** adopted as a second charter (one source of truth — this file). The genuinely new, concrete,
on-brand rules are folded in below and applied per screen in the normal gate-green rhythm. Items that
fight our constraints are recorded with the required change so the limitation stays traceable.

**Adopt (new, low-risk, high-value):**
- **Data into meaning.** Never show a raw number where an insight fits: pair the count with the thing
  that needs attention ("245 invoices → 32 overdue today"; "stock ≈ 8 orders left"). Dashboard/KPI first.
- **Context before action.** No isolated `[Approve]`/`[Post]` — the primary action states *what* is
  being acted on and its impact (amount, party, reversibility) right next to the button.
- **Human-language statuses.** Render workflow statuses as plain states ("Waiting for Finance approval")
  — **display-layer mapping only**, never changing the status enum / state machine, and **always via
  i18n keys with ar/en parity** (no hardcoded strings, or gate03 fails).
- **Navigation extras.** Breadcrumbs, recent pages, favorites in the shell — additive, logical-CSS.
- **Explain before asking.** Complex forms get a one-line purpose + what-happens-after (reuse the help
  content already authored per route).

**Adopt with a required change:**
- **Forms autosave → explicit draft-save.** Do **not** silently autosave accounting/order/journal
  forms (a half-entered journal autosaving is unsafe and breaks the confidence rule). Offer an explicit
  "Save draft" only where a draft entity already exists.
- **Single icon library.** Fine to standardize on Lucide/Tabler/Heroicons, but it must be **bundled
  offline** (no CDN) per the customer-hosted "no cloud deps" rule. Low priority (current custom set works).

**Defer / out of scope here:**
- **AI assistant / "workflow intelligence layer."** A real feature with real scope (likely an LLM
  integration → cost + offline/on-prem hosting concerns) — its own future stage, not UI polish.
- **Column resize / pinning.** Low value for the effort right now.
- **"Retention" framing** (doc 1). Kept as a north star only; an internal ERP earns use by being the
  job tool — no consumer engagement mechanics.

- **Implemented 2026-06-19 — dark mode.** A full dark theme implemented as a **pure token remap**:
  `tokens.css` overrides only the semantic colour layer (+ shadows / focus ring) under
  `:root[data-theme="dark"]`, so every component that already uses `var(--color-*)` flips with zero
  per-component change — the design-token discipline paying off. **Identity preserved by inversion,
  not a new hue:** the light theme's high-contrast near-black primary/logo becomes a near-white one on
  a near-black canvas (same monochrome "Conductor" character); `-strong` variants become more luminous
  (readable text on dark), `-subtle` variants become dark translucent tints (chips/fills) so existing
  strong-on-subtle pairings keep contrast. Toggle (`src/theme.ts` + `app/ThemeToggle.tsx`, sun/moon)
  lives in the command bar and the login head; choice persists to `localStorage["erp.theme"]`; an
  **early inline script in `index.html`** applies the stored/system theme before first paint (no FOUC),
  and `color-scheme` is set per theme for native controls. First visit follows the OS
  `prefers-color-scheme`. New i18n `theme.*` keys (ar/en parity). Verified in-browser: toggle +
  persistence + no-flash reload across login → dashboard → order detail, light↔dark round-trip; gate03
  green. (Known follow-up: the React-Flow workflow canvas keeps some of its own default colours — not
  yet themed.)
- **Implemented 2026-06-19 — data-into-meaning + human-language statuses.** Dashboard gained a
  **"Needs attention today"** panel (`DashboardPage.AttentionPanel`): turns raw module data into the
  few decisions/risks to act on now — pending sales/purchase approvals, outstanding receivables /
  supplier bills (amount + count), SLA-breached tickets, failed messages — each a one-line insight
  linking to the right screen; problem signals carry a danger/warn tint, and a calm "all clear" line
  shows when there's nothing. Cross-module signals are fetched defensively (`.catch(() => [])`) so a
  role without access or an unreachable module never breaks the dashboard. Order & purchase-order
  **detail pages** now show a plain-language status line under the badge ("Invoiced — awaiting payment
  of …"; "Waiting for a manager's approval before it can be confirmed") — display-layer only, the
  status enum/lifecycle is untouched; new `sales.statusExplain` / `purchasing.statusExplain` i18n keys
  with ar/en parity. gate:all 00–11 green.
