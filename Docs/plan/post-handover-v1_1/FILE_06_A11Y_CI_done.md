# FILE_06 — a11y check (axe-core) on top RTL screens

## Finding
No automated accessibility check exists anywhere in the repo — brand/UX review (`conductor-brand`,
`brand-philosophy-review`) covers *judgment* (contrast, monochrome chrome, designed states) by eye,
but nothing catches mechanical a11y regressions (missing labels, bad landmark roles, contrast
ratio drift) automatically. `apps/web/e2e` already has an authenticated Playwright suite (ar+en
projects, ar/RTL first) from `twenty-harvest/FILE_04` — the natural home for this.

## Dependency decision (team rule 7 — no new dep without asking)
**`@axe-core/playwright`** (dev-only, not shipped) — the standard axe-core wrapper for Playwright,
gives an `AxeBuilder` that scans a live page and returns violations by WCAG rule + impact. Founder
approved via the `/erp-resume` Phase-2 picker (2026-07-23) — logged in `DECISIONS.md`.

## Tasks
- [ ] `npm install --save-dev @axe-core/playwright` in `apps/web`.
- [ ] `e2e/lib/a11y.ts` — `expectNoSeriousA11yViolations(page)` helper: run `AxeBuilder`, filter to
      `serious`/`critical` impact (moderate/minor deferred — first pass sets the bar, not the
      ceiling), assert empty with a readable failure message (rule id + selector + help URL).
- [ ] `e2e/specs/a11y.spec.ts` — one spec, reuses the existing authenticated `page` fixture (so it
      runs under both `ar` and `en` projects automatically, ar/RTL first per the suite's existing
      order) — scans the top screens: Dashboard (`/`), Sales Orders (`/sales`), Purchasing
      (`/purchasing`), Accounting Journals (`/accounting/journals`), Inventory Stock-on-hand
      (`/inventory`), CRM Pipeline (`/crm`), a representative create-form (`/sales/orders/new`),
      Settings → Accessibility (`/settings/accessibility`).
- [ ] Run against the seeded live dev env (`run-dev.ps1`), ar first — fix any real `serious`/
      `critical` violations found (small, scoped fixes only; don't scope-creep into a full a11y
      audit).
- [ ] Add to `Docs/RUNBOOK.md` "Regression run before every release" alongside `npm run e2e` — NOT
      wired into `.github/workflows/ci.yml` (matches `twenty-harvest/FILE_04`'s own precedent: e2e
      needs a live server, so it's a release-time step, not a push/PR gate).

## Watch
- Reuse the existing `test`/`page`/`t` fixtures from `e2e/lib/fixtures.ts` — don't hand-roll a new
  login path.
- Zero-tolerance on `serious`+`critical` only for v1 — a strict zero-violations bar (incl.
  minor/moderate) would likely fail on pre-existing, lower-priority issues out of scope for a
  "Small" Nice-to-Have; tightening the bar is a natural follow-up, not this session.

## Done when
`npx playwright test -c e2e/playwright.config.ts a11y` (or `npm run e2e -- a11y`) runs green
against the seeded dev env, ar project first; a deliberately-removed `<label>` (local, reverted)
fails the spec with a readable axe rule id.

## How to test
- `cd apps/web && npm run e2e -- a11y` (needs `run-dev.ps1` running + seeded DB).
- Break a label/aria attribute on one of the 8 screens → the spec fails naming the rule.

## Closed 2026-07-23 (A, `C:\AhmedGaid\ERP`)
`@axe-core/playwright` added; `e2e/lib/a11y.ts` + `e2e/specs/a11y.spec.ts` built; wired into
`Docs/RUNBOOK.md` §8 alongside `npm run e2e` (not `.github/workflows/ci.yml` — matches the rest of
the e2e suite's release-step precedent). First live run found 4 real issues, 3 fixed + 1 flagged —
full detail in `DECISIONS.md` ("a11y check" entry): purchasing/inventory module-accent contrast
(fixed), `--color-text-muted` borderline miss on its own companion surface (fixed), missing
`aria-label` on 3 new-order line-item inputs (fixed), `--color-text-subtle`'s deliberately-faint
default (flagged, not fixed — opt-in `data-contrast="high"` already mitigates it, founder call on
tightening the default). Suite green: 18/18 (8 screens × ar/en + 2 auth setup). Also fixed a spec
bug found along the way — `page.waitForLoadState("networkidle")` hung on screens with background
polling, timing out and cascading into the login endpoint's 429 rate limit via worker recycling;
replaced with `domcontentloaded` + a bounded 2s settle (matches the rest of the suite's wait style).
Gates green: i18n parity 2634, `tsc -b` clean, gate03 exit 0, Vitest 52/52.
