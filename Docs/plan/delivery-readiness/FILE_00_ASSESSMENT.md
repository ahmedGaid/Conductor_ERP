# Delivery-Readiness Assessment — Conductor ERP

**Goal (user, 2026-07-15):** prepare the app to hand to a **customer who will run it live as a
business**. Every **non-AI** feature must be verified working end-to-end (drive + fix + report).
Finish non-AI work-in-progress first. AI (`assistant`, ai-reliability, RAG, eval) is **out of scope**
for this pass.

**This file = the map + the multi-session program.** Phase 0 (ground truth) is DONE and recorded
below. Later phases each = one session with a pasteable `/goal`.

---

## Phase 0 — Ground truth (DONE 2026-07-15)

The app is in **genuinely good shape**. Baseline evidence:

| Check | Result |
|---|---|
| Gate suite `scripts/gates/_run.py all` (00–15) | **ALL GREEN** (gate 15 = AI eval 74.3%, above threshold; skippable) |
| Backend API smoke (48 non-AI GET endpoints, authed as admin) | **48/48 behave correctly** — 45×200; 3×400 are *correct required-param validation*, not bugs (general-ledger needs `account`; vat-return needs `from`/`to`; audit needs `entity_type`+`entity_id`) |
| Frontend boot (Vite :5173) | Boots; login works; Arabic/RTL default |
| Dashboard | Renders with real data (revenue 10,208 · expenses 8,800 · net 1,408 EGP), ⌘K command bar, "needs attention" feed |
| Accounting report render (trial balance) | 15 accounts, **debits = credits = 1,369,551.96 EGP, balanced** — double-entry engine sound |
| Sales write form (new order) | 5-step flow (create→confirm→deliver→invoice→collect), customer picker populated |

**Verdict:** read paths, reports, and the app shell are healthy. The app is close to deliverable.
Remaining work is (a) finish invisible non-AI WIP, (b) verify **write/mutation** flows E2E,
(c) production/business-run hardening, (d) handover docs.

### Feature inventory (non-AI)

| Module | Route(s) | Status |
|---|---|---|
| Identity / RBAC | `/admin/users`, `/admin/roles` | API OK — needs E2E write verify |
| Sales | `/sales/*` (orders, quotations, customers, invoice) | API OK, forms render — needs full order→invoice→collect drive |
| Purchasing | `/purchasing/*` (orders, requests, suppliers, import) | API OK — needs E2E write verify |
| Inventory | `/inventory/*` (items, warehouses, movements, counts, batches, stock-on-hand) | API OK — needs movement/count E2E |
| Pricing | `/pricing/*` | API OK — needs resolve/assignment E2E |
| Accounting | `/accounting/*` (COA, journals, TB, GL, P&L, BS, cash-flow, VAT, assets, cost-centers, bank-rec, budgets, report-builder) | API OK, TB balanced — needs journal-post + report cross-check |
| E-Invoice (ETA) | `/einvoice` | API OK — needs submit/sign flow verify (ETA sandbox creds = user) |
| CRM | `/crm/*` (pipeline, opportunities, leads, tickets, campaigns) | API OK — needs E2E write verify |
| Notifications | `/notifications` | API OK |
| Workflows | `/workflows`, `/instances` | API OK — needs run-a-workflow E2E |
| Setup wizard | `/setup` | API OK — critical for a NEW customer's first-run |
| **Smart-import** | *(no SPA route — engine only)* | **WIP 4/17** — invisible; finishing = product decision, NOT a visible-app blocker |

**AI (skipped this pass):** `/assistant`, `/assistant/knowledge`, `/assistant/ops`,
ai-reliability, RAG, eval harness.

---

## Known issues found in Phase 0

1. **Demo cash balance −1,116,759.86 EGP** on dashboard — seed artifact (large fixed-asset
   purchase credits Cash). Books still balance. Not a code bug, but **demo seed data is not
   clean enough to hand to a customer** as a first impression. → address in Phase 3 (fresh-tenant
   seed / clean demo profile).

*(No functional bugs found yet. Write-flow bugs, if any, surface in Phase 1.)*

---

## The program (each phase = one session)

### Phase 1 — E2E write-flow verification + fix (the "drive + fix + report" core)
Drive each module's **mutation** flows in the real browser as `admin`, fix what breaks, log
results. Split across sessions by module cluster:
- **1a Sales+Inventory:** create order → confirm → deliver (stock issue) → invoice → collect;
  confirm stock-on-hand + journal postings move correctly.
- **1b Purchasing+Accounting:** PR → PO → receive (GRNI) → supplier invoice → payment;
  post a manual journal; re-check trial balance still balances.
- **1c CRM+Pricing+Workflows:** lead→opportunity→win; assign price list, resolve price;
  run one workflow instance to completion.
- **1d Identity+Setup:** create a user, assign role, verify RBAC denies; run the setup wizard
  clean. Verify a non-admin role sees only permitted nav/actions.
Each session appends a PASS/FAIL table to `FILE_01_E2E_RESULTS.md` (create it) and fixes
root-cause any FAIL (+ regression test).

### Phase 2 — Finish non-AI WIP (smart-import) — **DECIDED 2026-07-16: (a) DEFER**
Smart-import is at FILE_06 (analyze/validate) of 17. It has **no UI**, so it is not a visible
broken feature — deferring costs nothing for handover. User confirmed: ship handover without it;
remaining FILE_07–17 stay parked at their existing master-roadmap queue position (pos 8, paused)
for a later session, not part of this delivery track.

### Phase 3 — Business-run hardening (production readiness)
- Clean first-run data: a customer starts from **setup wizard + empty books**, not demo clutter.
  Verify `seed_identity`/`seed_accounting` give a sane empty tenant; keep `seed_demo` dev-only.
  **[DONE 2026-07-16 — verified empirically on a throwaway DB (`erp_seedtest`, dropped after).
  After `migrate` + `seed_identity` + `seed_accounting` the tenant has EMPTY BOOKS and ZERO demo
  business data: 0 JournalEntry/JournalLine, 0 Customer/SalesOrder, 0 Item, 0 Supplier/PurchaseOrder,
  0 Lead, 0 PriceList. Only baseline scaffold present — 27 CoA Accounts, 1 FiscalYear + 12 Periods,
  2 TaxCodes, 3 CostCenters, HQ Branch, RBAC (181 RolePermission + 9 ApprovalLimit), 3 Departments +
  2 Teams, 3 assistant.Budget (AI, off without key). `seed_accounting` == the same
  `seed_baseline_accounting()` the setup wizard calls, so first-run and CLI provision identically.
  `seed_demo` confirmed **standalone script**, wired into NO prod/setup path (only tests/gate01 use
  `seed_identity`); RUNBOOK already warns "DEV demo data only — do NOT run on a real customer
  install". FINDING (not a bug, recommend before handover): `seed_identity` also creates 3 NON-admin
  demo users (manager/accountant/auditor) sharing the known password `Dev12345!` → default-credential
  clutter on a customer tenant. Recommend a customer-safe provisioning path (admin-only, or a
  `--no-demo-users` flag / separate `provision_tenant` command) so the handover tenant ships with one
  admin whose password the customer sets. Deferred: touching `seed_identity` risks gate01/test_access
  which call it — do it as its own small slice with the tests updated.]**
- Security pass: `Docs/plan/00-security-hardening.md` checklist — secrets, DEBUG off, ALLOWED_HOSTS,
  HTTPS, JWT/cookie flags, rate limits, admin lockdown. **[DONE 2026-07-16 — `check --deploy` clean
  under prod with a real secret; prod.py already sets HSTS/CSP/secure-cookie/SSL-redirect. Code-level
  scope/SSRF audit from 00-security-hardening.md still owed as its own slice.]**
- Env/config: `.env.example` complete; production `settings` profile; DB backup guidance.
  **[DONE 2026-07-16 — `.env.example` rewritten to document the full ~40-key env surface (Django core,
  DB, Redis, Celery, storage, security/HTTPS, DRF throttles, workflow egress, email, optional AI);
  dead `DEV_USER_*` keys removed. Prod profile verified. DB backup guidance still owed (→ RUNBOOK).]**
- Deploy runbook: verify `Docs/RUNBOOK.md` matches reality; a business can stand it up.
- **User actions (not Claude):** real ETA credentials, real DB/prod hosting, real admin password.

### Phase 4 — Handover package — **DONE 2026-07-16**
- One-page "how to run Conductor" for the business (login, first setup, daily flows) — AR + EN.
  → `FILE_02_HANDOVER_GUIDE.md`
- Known-issues / not-included list (AI is off, smart-import status, any Phase 1 deferrals).
  → `FILE_03_KNOWN_ISSUES.md`
- Final full-drive smoke + sign-off checklist. → `FILE_04_SIGNOFF_CHECKLIST.md`

---

## Session protocol
One phase-slice per session. After each: gates green, results file updated, `erp-status` updated,
STOP, fresh session. This file is the progress bar — mark slices done as they land.
