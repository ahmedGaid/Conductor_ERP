# FILE_05 — Archiving + acceptance — done note

**Status: plumbing DONE + mock-tested (2026-07-21). Real-sandbox acceptance run PENDING founder creds.**

## What was built (mock-testable, landed)

- **Retention archive.** `ETAInvoiceArchive` (OneToOne → `ETAInvoice`, migration `0007`) stores the
  **exact submitted document + raw ETA response** verbatim, with `document_hash`, `archived_at`, and a
  `simulated` flag. Separate table so the JSON blobs stay off the hot list query. Basis: ETA + Egyptian
  Tax Procedures Law No. 206/2020 art. 37 → **5-year** retention, satisfied by never auto-deleting.
- **Populated at submit.** `SubmitResult` carries `document`/`raw_response`; `eta_adapter.submit` fills
  them; `issue.submit_invoice` archives on the accepted path with `simulated = not is_live()`.
- **Retrieval path.** `GET /api/einvoice/invoices/{id}/document` → the archived document + ETA
  identifiers + status + `simulated`. 404 before submit. Frontend "Download document" row action saves
  `einvoice-<invoice>.json` (ar/en).
- **gate10 real-sandbox smoke — opt-in.** Off by default (CI proves the simulated path, stays green
  with no creds). `GATE10_ETA_SANDBOX=1` drives one live round-trip via `manage.py eta_sandbox_smoke
  --poll` (no-ops exit-0 when unconfigured). gate10 also asserts the archive model + retrieval route.

Tests: `erp/einvoice/tests/test_archive.py` (5). `pytest erp/einvoice` = **96 passed**, gate10 green,
tsc (einvoice) + i18n parity clean.

## Acceptance run — PENDING (STOP-gate)

The end-to-end proof (real order → invoice → submit → sign → `valid` → archived) needs founder-supplied
ETA pre-production credentials + company tax profile (`ETA_ISSUER_*`, RIN) + signing cert
(`ETA_SIGNING_PFX_*`). When they arrive:

1. Configure ETA in Settings → E-Invoicing (or `ETA_*` env), enable, click **Test connection**.
2. Run `GATE10_ETA_SANDBOX=1 .\.venv\Scripts\python.exe scripts\gates\_run.py 10`
   (or `manage.py eta_sandbox_smoke --poll` directly).
3. Confirm: submission accepted → UUID/longId returned → poll → `valid` → `ETAInvoiceArchive` row
   holds the signed document with `simulated=False`; retrieval endpoint returns it.
4. Record the run result + screenshots below, flip `pre-handover-hardening/FILE_01` Branch A to
   satisfied if that branch was chosen, and update the `erp-e-invoice` status skill.

### Result (fill in after the real run)
- Date / operator:
- Environment (must be pre-production):
- Submission UUID / long ID:
- Poll verdict:
- Archive verified (`simulated=False`, document retrievable):
- Screenshots:
