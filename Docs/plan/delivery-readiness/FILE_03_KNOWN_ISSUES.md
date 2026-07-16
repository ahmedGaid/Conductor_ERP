# Known Issues / Not Included — Handover

Everything below is known and accepted at handover. None block go-live for non-AI operation.

## Out of scope this pass (by design)
- **AI features disabled**: `/assistant`, AI copilot, RAG knowledge search, ai-reliability harness.
  No API key configured. Turning this on is a separate, later engagement.

## Deferred (product decision, not a bug)
- **Smart-import** (bulk CSV/Excel import engine): built through analyze/validate stage only
  (4/17 planned steps), **no UI exposes it**. Invisible to the customer — deferred to a future
  session, not a handover blocker.

## Gaps flagged during Phase 1 E2E verification (not bugs — missing surface)
- **No partial payment/collection in the UI.** Sales "collect" and Purchasing "register payment"
  always settle the full outstanding balance in one click. The service layer supports partial
  amounts; no UI path exposes it yet. Flag if the customer needs partial receipts/payments.
- **E-Invoice (ETA) submit/sign flow unverified.** API wiring is in place but untested end-to-end
  — requires real Egyptian Tax Authority sandbox/production credentials, which only the customer
  or business owner can provide. Test this as the very first live action once credentials exist.
- **Workflow visual builder** (drag-and-drop canvas): create/run lifecycle is verified via API and
  through the real UI Run button; the canvas's node-to-node edge-drawing by mouse drag was not
  exercised in this pass (headless browser limitation, not a code defect). Recommend a 2-minute
  human smoke test (drag start→end, Save, Run) before relying on it for a new automation.

## Environment cleanup owed before a real customer sees the data
- **Demo/seed data is dev-only and must not be used for a live customer.** `seed_demo` is a
  standalone script, not wired into any production or setup path — do not run it against a real
  install. `seed_identity` + `seed_accounting` alone give a clean empty tenant.
- **Test artifacts left in the current demo database** from Phase 1 E2E drives (harmless, dev DB
  only — do not carry into a fresh customer install): sales order SO-2026-000017, PO-2026-000012,
  CRM opportunity OPP-2026-000005, lead LEAD-2026-000003, a STANDARD price-list line for GADGET,
  workflow "Phase1c QA Automation" + one completed run, user `phase1d_qa`, and branch `ALEX`
(inactive, created verifying the new Branch admin UI). **Action for a real
  handover: provision the customer's tenant from a fresh database using `seed_identity` +
  `seed_accounting` only — do not clone this dev database.**
- **`seed_identity` also creates 3 demo non-admin users** (manager/accountant/auditor) sharing the
  known password `Dev12345!`. Fine for internal demos; on a real customer install, either delete
  these before go-live or have the customer change every password immediately.

## One bug found and fixed during this readiness pass
- Two price lists both had `is_default=True` (seed script bypassed the single-default invariant),
  making some items unreachable in price resolution. Fixed in `scripts/seed_demo.py`
  (`set_single_default()` used everywhere now) + regression test
  `erp/pricing/tests/test_resolve.py::test_set_single_default_demotes_other_defaults`. No further
  action needed.

## Demo-only cosmetic artifact (not present in a fresh install)
- The current demo database's dashboard shows a negative cash balance from a large seeded
  fixed-asset purchase. This is a seed-data artifact, not a code bug, and does not appear in a
  freshly provisioned tenant (verified empty-books on `seed_identity`+`seed_accounting`).
