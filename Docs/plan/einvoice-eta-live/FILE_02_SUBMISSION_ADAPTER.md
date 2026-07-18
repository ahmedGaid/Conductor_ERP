# FILE_02 — Real submission adapter  (Large)

## Goal
Replace the stub `eta_adapter.submit()` with a real ETA document submission: build the ETA document
JSON from `ETAInvoice`, POST it via `eta_client`, parse the real ETA response (submission UUID,
long-id, validation status), map errors to actionable states. Signing lands in FILE_03 — here, wire
the unsigned-or-hash submission path and full response handling first.

## Before you start (read)
- `erp/einvoice/services/eta_adapter.py`, `services/issue.py`, `domain/models.py`
- FILE_01's `eta_client.py`
- Current ETA API doc: document schema, submit endpoint, response/error codes (look up — cite)

## Tasks
- [ ] Map `ETAInvoice` → ETA document JSON (issuer/receiver, line items, taxes, totals in the
      units ETA expects; money is minor units internally — convert at the edge only).
- [ ] `submit()` calls the real endpoint via `eta_client`; store the returned submission UUID +
      long-id on `ETAInvoice`.
- [ ] Map ETA response codes → states (`submitted`, `rejected` with reason, transient→retryable).
      Rejections carry the ETA error text into a human, blame-free UI message.
- [ ] Keep idempotency: re-submitting the same invoice does not double-submit.
- [ ] `@transaction.atomic` around state transitions; every transition still calls `audit.record`.

## Watch
- ETA document schema is exact and versioned — build it from the live spec, validate field-by-field
  against a sandbox echo before trusting it.
- Do not break `gate10`'s event-only decoupling (no cross-module import).

## Done when
A seeded invoice submits to the ETA sandbox and comes back with a real submission UUID + status;
rejections surface a readable reason; re-submit is a no-op. gate10 still green.

## How to test
- Sandbox submit a valid invoice → real UUID stored, state `submitted`.
- Submit a deliberately invalid one → `rejected` with the ETA reason shown, no crash.
- Re-submit → idempotent. `pytest erp/einvoice` + `gate10` green.
