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

### Attempt log — 2026-07-26 (blocked, no fabricated result)

Checked every candidate source for real ETA preprod credentials before touching Settings →
E-Invoicing:
- `Docs/E invoice/` (all files) — regulatory/legal PDFs (law 188/2023, GS1, decree 289) + a generic
  ETA self-registration walkthrough (`E-INVOICING-SELF-REGISTRATION.pdf`, screenshots show demo
  data `Taxpayer1`/`113317713`) + seminars/docx. **No client_id/secret/RIN/signing cert anywhere.**
- Repo `.env` — 0 `ETA_*` keys set.
- DB `ETASettings` (admin-config pivot row `00000000-0000-0000-0000-000000000001`) —
  `environment=""`, `client_id=""`, `enabled=False`. Untouched default.
- No `.pfx`/`.p12` file anywhere in the repo tree.

**Conclusion: real ETA pre-production credentials + signing cert have not been issued/supplied yet.**
Obtaining them is a founder-side action outside this repo: complete self-registration at
`https://profile.eta.gov.eg/signUp` (needs a USB e-signature token + ITIDA e-seal certificate +
company tax registration number + national ID — Windows-only client, per the guide), which yields
a portal login, from which the preprod API `client_id`/`client_secret`/RIN and a signing PFX are
obtained separately. No document in the repo substitutes for this. Did not run
`eta_sandbox_smoke`/gate10 against fake values — a "success" there would be meaningless (and against
the claims-discipline rule: nothing may claim a Tax-Authority verdict without `is_live()`).
Stopping here per the session goal's exit clause; plumbing remains fully built and mock-tested,
STOP-gate unchanged.

**Follow-up (same day):** also opened the 4 `.docx` files (binary — extracted via zip/XML, not
directly Read-able): `شرح المستندات المطلوبة.docx`, `نسخة_طلب_اصدار_فواتير_عن_طريق_البورتال.docx`,
`ضرائب 3.docx` — all company-registration/portal-application letters, e-signature vendor (Egypt
Trust) process steps, and invoice-count threshold rules (200/222 invoices/month decides portal vs
ERP-integration path). `نسخة_مقدم_لمصلحة_الضرائب_المصرية.docx` filename has no matching file on disk
(only the other three exist). Confirms: obtaining ETA preprod API creds + signing cert is a
physical government/vendor process (board-chairman signature, national ID, in-person office visit
to Egypt Trust) — no document contains issued credentials to copy in. Investigation exhausted.
