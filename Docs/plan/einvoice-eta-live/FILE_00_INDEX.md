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
2. ~~**Real credentials never touch the repo.** ETA client-id/secret come from env/secrets only.~~
   **REVERSED 2026-07-21 (founder):** the admin configures the whole connection **in-app**. Config
   now lives in the `ETASettings` singleton with the client secret **encrypted at rest** (Fernet);
   env `ETA_*` stays a valid fallback. The secret is still never serialized to a client, logged, or
   shown in the status panel (presence only). See DECISIONS "einvoice: ETA connection is configured
   in-app…". Built in the admin-config slice below.
3. **Sandbox first, always.** Every submission path is proven against the ETA sandbox/pre-prod
   before any real invoice. gate10 gains an (opt-in, credential-gated) real-sandbox smoke.
4. **Verify the ETA API contract against current official docs at build time** — the API version,
   endpoints, and signing rules change; treat the spec as volatile (look it up, cite it in
   DECISIONS), never from memory.
5. **New dependency = STOP-gate.** A signing/HTTP library needs a DECISIONS entry before install.

## Merge checkpoint
After FILE_03 (signing proven in sandbox) and after FILE_05 (acceptance) — full gate run green
first, then merge.

## Admin-config pivot (2026-07-21) — DONE (foundation slice)

Founder asked for all ETA config to be done by the admin in-app, including connecting to the
pre-production portal and testing, so the integration is production-ready the moment real company
credentials arrive. Delivered this session (backend fully tested; frontend type-clean + gates green):

- **`ETASettings` singleton** (encrypted client secret) + migration `0003_etasettings`.
- **`services/secrets.py`** (Fernet encrypt/decrypt, key from `ETA_SECRET_KEY` or derived).
- **`services/config.py`** resolver — DB-first, env fallback; `eta_client` refactored to read it.
- **Admin API** `GET/PUT /api/einvoice/config` + `POST /api/einvoice/config/test` (System-Admin).
- **Settings → E-Invoicing** page (ar/en) — fields + "Test connection" + honest "still simulated"
  banner.
- Tests: `erp/einvoice/tests/test_config.py` (encryption, resolver, admin API, secret-never-leaks,
  test-connection mapping). `pytest erp/einvoice` = 47 passed.

**Still STOP-gated for a real end-to-end test:** actual ETA pre-production credentials + the
company tax profile. Once the admin enters them and clicks Test connection, FILE_02 (real submission
adapter) is the next build — the connection/auth half is done, the document-submission half is not.

## Change log
- **2026-07-18 — Created** from the QA audit's Critical e-invoicing finding. Positioned in
  `EXECUTION_ORDER.md` as pos 8-C; blocks handover only if `pre-handover-hardening/FILE_01` picks
  Branch A.
- **2026-07-21 — Admin-config pivot** (see section above): config moved in-app, secret encrypted at
  rest, reversing locked decision #2. Foundation slice built; FILE_02+ unchanged.
