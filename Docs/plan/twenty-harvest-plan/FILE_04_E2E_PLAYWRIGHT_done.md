# SESSION 4 — Playwright E2E Suite  ⛔ DECISIONS GATE FIRST
# Files: apps/web/e2e/ (new), apps/web/package.json (dev-dep — GATED), Docs/RUNBOOK.md, DECISIONS.md

Twenty reference: a dedicated `twenty-e2e-testing` Playwright package — the frontend has a
regression net beyond typecheck. Our known gap ("no JS unit runner") is closed here NOT with a
unit runner debate, but by encoding the delivery-track browser drives we already paid to learn.

---

## STOP — dependency decision (team rule 7)

`@playwright/test` is a NEW dev-dependency. Before anything: present the founder ONE decision —
**Option A (recommended):** add `@playwright/test` (dev-only, not shipped to customers) and
write the suite. **Option B (fallback):** no new dependency — instead formalize
`Docs/testing/E2E_MASTER_PROMPT.md` (the agent-driven daily E2E) as the ONLY regression net and
extend its journey list with the Tier-1 features. Write the choice to DECISIONS.md, then
proceed (A) or trim this session to the prompt-file update (B).

---

## Before You Start (Option A path)

1. Read `Docs/plan/delivery-readiness/FILE_01_E2E_RESULTS.md` → the exact drives that passed
   (Sales/Inventory, Purchasing/Accounting, CRM/Pricing/Workflows). These ARE the spec list.
2. Open `run-dev.ps1` → ports and startup; `scripts/seed_demo.py` → known seeded data + logins.
3. Open `apps/web/package.json` scripts → naming idiom for the new `e2e` script.

"Do not write anything yet."

---

## Task A — Harness

`apps/web/e2e/playwright.config.ts`: baseURL `http://localhost:8000` (WhiteNoise-served build)
or `:5173` (vite dev) via env; NO webServer autostart (the dev env is `run-dev.ps1`, documented
prerequisite); trace on first retry; both `ar` (default) and `en` projects — ar runs FIRST.
Login helper using seeded `admin` credentials from env (never hardcoded).

## Task B — Specs (one file per journey, assertions at the business layer)

1. `sales.spec.ts` — create order → confirm → deliver → invoice → collect; totals in integer
   minor units asserted via API response, formatted EGP asserted in UI.
2. `purchasing.spec.ts` — PR → PO → receive → invoice → 3-way match → payment.
3. `accounting.spec.ts` — manual journal (balanced) → trial balance still balances.
4. `crm-pricing.spec.ts` — lead → convert; price-list resolution shows the expected tier.
5. `workflow.spec.ts` — run an existing workflow, assert completion state.

Selectors: prefer roles/labels (works in both languages via i18n keys → use `data-testid` only
where labels are dynamic). RTL: the ar project asserts `dir="rtl"` on the app root.

## Task C — Wiring

`npm run e2e` script; RUNBOOK section "Regression run before every release: seed → run-dev →
npm run e2e (ar first)". NOT added to default gates (needs a live server) — it's a release
step, like the gate16 drill.

---

## Smoke Test

- [x] DECISIONS entry written (A or B) BEFORE any install
- [x] (A) `npm run e2e` green on the seeded dev env, ar project first
- [x] (A) One deliberate UI break (local, reverted) fails the right spec with a readable trace
- [x] `npx tsc -b` still green; no new prod dependency in the bundle

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_05_WEBHOOKS.md in a FRESH session.
```
