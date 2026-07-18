# FILE_02 — Calm milestone moments (done 2026-07-19)

## Scope
Useful, quiet delight when the company crosses a real milestone — first profitable month, a round
invoice count — as a gentle, dismissible acknowledgment. **No confetti, no sound.**

## What shipped
- **Backend** — `erp/monitoring/models.py` (`MilestoneAck`, one row per milestone key ever shown —
  company-wide, not per-user: a single-tenant install has one "first profitable month", dismissed
  once for everyone, never a per-login nag), `erp/monitoring/milestones.py`:
  - `GET /api/dashboard/milestones/` — the single highest-priority pending milestone, or `null`.
    At most one shown at a time (a flood of banners isn't calm).
  - `POST /api/dashboard/milestones/<key>/dismiss/` — idempotent (`get_or_create`), company-wide.
  - Two milestone kinds, checked invoice-count first then profit (order is arbitrary — both are
    real, this just picks one at a time): `invoice_count` fires at round thresholds (100 / 500 /
    1,000 / 5,000 / 10,000 / 50,000 / 100,000 — highest crossed, not yet acked) via a new
    `erp.sales.contracts.invoiced_order_count()` (company-wide count of orders at Invoiced/Paid
    status); `first_profitable_month` fires when the current month's net income is positive and
    that key hasn't been acked yet.
  - Migration `erp/monitoring/migrations/0001_initial.py`.
- **Frontend** — `apps/web/src/api/milestones.ts` (client), `apps/web/src/pages/MilestoneBanner.tsx`
  (new, mirrors `GettingStarted.tsx`'s dismiss pattern but backend-persisted instead of
  localStorage), mounted in `DashboardPage.tsx` right under `GettingStarted`. CSS
  `.dash__milestone-*` in `DashboardPage.css`.
- **i18n** — `dashboard.milestone.*` (invoiceCount with `{{count}}`, firstProfitableMonth,
  dismiss), ar + en.

## Bug found and fixed during live verification
Both new API client functions (`milestones.ts`, and `confidence.ts` from FILE_01) called their
endpoints without a trailing slash. GET requests silently ate a wasted 301 round-trip (Django's
`APPEND_SLASH` redirects them); the milestone dismiss **POST** hit Django's documented failure
mode instead — `APPEND_SLASH` can't redirect a POST without dropping its body, so Django raises
`RuntimeError` → a 500. Fixed all three call sites to include the trailing slash.

## Verified
- `pytest erp/monitoring erp/sales` — 131 passed (7 new milestone tests: no-milestone-by-default,
  fires-once-crossed, picks-highest-threshold, dismiss-is-idempotent-and-company-wide,
  first-profitable-month, at-most-one-shown-at-a-time, anonymous-401/403).
- `node scripts/check-i18n-parity.mjs` — 2033 keys, ar/en parity green.
- `npx tsc -b` — clean (after fixing a `number | null` vs `number` mismatch on the `invoiceCount`
  i18n interpolation).
- `python scripts/gates/gate03.py` — green.
- **Live (rung 3):** same temp-local-Django-on-:8010 pattern as FILE_01 (port 8000 still occupied
  by the separate `erp-demo` docker stack, untouched). Real dev DB genuinely had a positive net
  income this month with zero prior ack — the banner fired for real ("This month is profitable —
  your first. Well done."), caught the trailing-slash 500 on first dismiss click, fixed, reloaded,
  clicked Dismiss again → 200 → banner gone → reloaded the whole page → **stayed gone** (server-side
  ack confirmed, not just local state). Reverted `vite.config.ts` and killed the temp Django
  process after.

## Deviations
- Milestone thresholds (100/500/1,000/…/100,000) and the two kinds are exactly the two the spec
  named — no invented third milestone, per "smallest change fully solving."
- `invoiced_order_count()` counts orders at INVOICED or PAID status, company-wide (not per-user
  scoped) — a milestone is a company fact, not a personal one, matching `low_stock()`'s existing
  company-wide precedent in `inventory.contracts`.
