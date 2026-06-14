# Phase 08 — Reference Use Case + End-to-End Proof

## Goal
Wire the seeded **Purchase Request Approval Flow** through the real UI + API + engine + adapters, and prove every
success criterion with an automated end-to-end test. No mocked happy path that hides the engine.

## Files to touch
- `apps/web/` — ensure the seeded workflow is loadable in the canvas, startable, and observable in the viewer
- `e2e/purchase-request.spec.ts` — Playwright
- `e2e/playwright.config.ts`
- `scripts/gates/gate08.ts` — boots api + web + mock ERP, runs Playwright, asserts DB state
- `scripts/dev-stack.ts` — one command to bring up db + api(+mock) + web for the e2e run

## End-to-end scenario (must run fully automated)
1. Seed DB (Phase 01) and start the stack (`scripts/dev-stack.ts`).
2. **Happy path (amount ≤ 50000):** start instance via UI → engine runs Start → `check_budget` (REAL REST call to
   mock ERP `/budget`) → `budget_gate` selects the approval branch → instance `waiting` at `manager_approval`.
3. In the execution viewer, click **approve** → instance `waiting` at `finance_approval` → approve →
   `create_po` runs as an **external write** (REST `POST /mock-erp/po` with idempotency key) → `notify_supplier`
   webhook fires → instance `completed`.
4. **Idempotency proof:** force `create_po` to retry with the same attempt key (simulate a transient failure +
   retry path) → assert exactly **one** row in `erp_external.purchase_orders`.
5. **Crash-resume proof:** start a second instance, advance to `waiting`, **kill the API process**, restart it,
   approve via API → instance resumes from the persisted state and completes. Assert each `NodeExecution` appears once.
6. **Reject path (or amount > 50000):** budget gate / approval reject routes to `end_rejected`; no PO row is created.

## Verification (gate:08) — encodes the brief's success criteria
- [ ] A workflow can be built+saved via UI (canvas round-trip from Phase 07 reused here).
- [ ] The seeded workflow runs end-to-end to `completed`.
- [ ] Execution viewer shows step-by-step node-level logs with statuses for the run.
- [ ] At least one real external REST call executed through the REST adapter (assert mock-ERP `/budget` + `/po` were hit).
- [ ] Manual approval paused (`waiting`) and resumed on approve; reject routes to the rejected branch.
- [ ] Killing the API mid-execution and restarting resumes the instance with no lost/duplicated `NodeExecution` rows.
- [ ] Retrying the ERP-write node created NO duplicate `purchase_orders` row (exactly one; UNIQUE held).
- [ ] The Purchase Request Approval Flow ran as the seeded reference example (workflow name asserted).
- [ ] gate08 exits 0 only when all of the above assert true (Playwright + direct DB queries).

## Done signal
The reference flow runs through the whole stack with real HTTP, real approvals, proven crash-resume and proven
idempotency. `gate:08` is green.
