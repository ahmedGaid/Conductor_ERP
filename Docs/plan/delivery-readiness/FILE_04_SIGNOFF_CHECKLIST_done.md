# Final Smoke + Sign-off Checklist — Handover

Run this once, on the environment that will actually go to the customer, before calling delivery
done. Check each box; anything unchecked is a blocker or a documented exception.

## 1. Gates (repo root, before packaging)
- [ ] `.\.venv\Scripts\python.exe scripts\gates\_run.py all` → 00–15 GREEN
- [ ] `apps/web`: `node scripts/check-i18n-parity.mjs` → clean
- [ ] `apps/web`: `npx tsc -b` → clean
- [ ] `python scripts/gates/gate03.py` (brand gate) → clean

## 2. Fresh-tenant provisioning (prove it, don't assume it)
- [ ] `migrate` on a clean database
- [ ] `seed_identity` (admin-only path, NOT the demo-users path) run — confirm only the intended
      admin account exists
- [ ] `seed_accounting` run — confirm empty books: 0 journal entries, 0 customers/orders, 0
      items/suppliers, chart of accounts + fiscal year + periods present
- [ ] Admin logs in, sets a real (non-default) password
- [ ] **Do NOT run `seed_demo`** on this environment — dev-only, confirmed standalone

## 3. Production config sanity
- [ ] `.env` filled from `.env.example` with real values (no placeholder secrets)
- [ ] `manage.py check --deploy` clean under the prod settings profile
- [ ] `DEBUG=False`, real `ALLOWED_HOSTS`, HTTPS in front of the app
- [ ] Redis reachable, Postgres reachable, both on real (not dev-default) credentials
- [ ] DB backup job scheduled per `Docs/RUNBOOK.md`

## 4. One full smoke drive per module (repeat of Phase 1, quick pass — not full E2E)
- [ ] Sales: create → confirm → deliver → invoice → collect on one order
- [ ] Purchasing: requisition → PO → receive → supplier invoice → payment on one order
- [ ] Inventory: stock-on-hand reflects the drive above
- [ ] Accounting: trial balance still balances (debits = credits); post one manual journal
- [ ] CRM: create one lead and one opportunity
- [ ] Pricing: resolve a price for at least one item, confirm exactly one default price list
- [ ] Workflows: run one existing automation to completion (or the 2-minute builder smoke:
      drag start→end, Save, Run)
- [ ] Identity/Setup: invite one real staff user, assign a role, confirm RBAC restricts their nav
- [ ] Setup wizard walked once clean (if this is a genuinely new tenant, not an upgraded one)

## 5. Cleanup
- [ ] No leftover QA/test users active (check for anything like `phase1d_qa` — should not exist
      on a real customer tenant provisioned per step 2)
- [ ] No leftover QA/test orders, opportunities, leads, or workflow runs (should not exist if
      provisioned per step 2, since fresh tenants start empty)

## 6. Handover materials delivered
- [ ] `FILE_02_HANDOVER_GUIDE.md` (AR+EN one-pager) given to the customer
- [ ] `FILE_03_KNOWN_ISSUES.md` reviewed with the customer — they explicitly accept AI-off,
      smart-import deferral, and the UI gaps (partial payment, branch UI, ETA untested)
- [ ] Customer has set their own admin password (not the delivery default)
- [ ] Real ETA credentials collected from the customer if e-invoicing is needed at go-live
      (otherwise explicitly deferred with their sign-off)

## Sign-off
- [ ] Customer/business owner confirms acceptance — name, date: ______________________
- [ ] Delivering engineer confirms all above checked or explicitly waived — name, date: __________
