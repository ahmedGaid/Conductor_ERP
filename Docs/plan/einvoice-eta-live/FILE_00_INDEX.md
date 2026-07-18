# E-Invoice ETA Live Integration — Master Index

> **The "invoice" plan.** Replaces the simulated `eta_adapter.py` stub with a real Egyptian Tax
> Authority (ETA) e-invoice submission. Whether this **blocks handover** is decided by
> `pre-handover-hardening/FILE_01` (Branch A = blocker, Branch B = post-handover). Do not start
> until that decision is recorded.

## Why this plan exists

`erp/einvoice/services/eta_adapter.py` is explicitly a stub: `document_hash()` is a SHA-256,
`submit()` returns a deterministic fake UUID — no real ETA call, no real signature. The lifecycle,
data model (`ETAInvoice`, money as minor units), event wiring (`sales.OrderInvoiced`), immutable
audit, and gate10 are all real and correct — **only the adapter is fake**. The stub's own docstring
says a real client requires swapping this one file. This plan does that swap properly:
credentials → signing → submission → status reconciliation → archiving → acceptance.

## Prerequisites (from the customer — STOP-gate)
- ETA portal registration + the company's tax profile (RIN/registration number, activity codes).
- ETA client credentials (client-id/secret) for the ERP as a registered integrator.
- Decision on signing method: ETA supports document hashing + (for some flows) a hardware/
  software signature. Confirm the exact ETA API version + signing requirement in force at go-live —
  **look it up against current ETA docs, do not assume.**

## The files (strict order; one file = one session)

| File | Task | Effort |
|---|---|---|
| FILE_01 | ETA credentials, sandbox env config, secrets handling (no secrets in repo) | Small–Med |
| FILE_02 | Real submission adapter — auth token, submit document, handle ETA response codes | Large |
| FILE_03 | Document signing per ETA's required method (validate against ETA sandbox) | Large |
| FILE_04 | Status reconciliation — poll ETA for valid/rejected, map to `ETAInvoice` states, retries | Medium |
| FILE_05 | Archiving + acceptance — long-term invoice storage, gate10 extended to real sandbox, sign-off | Medium |

## Locked decisions (re-confirm only if code/ETA-API contradicts)

1. **Swap one file, keep everything else.** The service layer (`issue.py`), model, events, and
   audit stay. Only `eta_adapter.py` (and new config/secrets) change. The adapter interface
   (`document_hash`, `submit`, `query`) is the seam.
2. **Real credentials never touch the repo.** ETA client-id/secret come from env/secrets only,
   surfaced by name (never value) in the operator status panel (`erp/monitoring/status_api.py`
   already does env-name-only reporting — extend it).
3. **Sandbox first, always.** Every submission path is proven against the ETA sandbox/pre-prod
   before any real invoice. gate10 gains an (opt-in, credential-gated) real-sandbox smoke.
4. **Verify the ETA API contract against current official docs at build time** — the API version,
   endpoints, and signing rules change; treat the spec as volatile (look it up, cite it in
   DECISIONS), never from memory.
5. **New dependency = STOP-gate.** A signing/HTTP library needs a DECISIONS entry before install.

## Merge checkpoint
After FILE_03 (signing proven in sandbox) and after FILE_05 (acceptance) — full gate run green
first, then merge.

## Change log
- **2026-07-18 — Created** from the QA audit's Critical e-invoicing finding. Positioned in
  `EXECUTION_ORDER.md` as pos 8-C; blocks handover only if `pre-handover-hardening/FILE_01` picks
  Branch A.
