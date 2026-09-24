# FILE_06 — Acceptance, runbook, issuing procedure, DECISIONS

**Model: Sonnet.** **Effort: Small.** Merge checkpoint after this file.

## Goal
Prove the whole flow end to end on a clean install, and write down how the founder actually
sells, issues, and renews a license — so it works without this conversation.

## Tasks
- [ ] **End-to-end drive on a fresh DB** (`provision_customer` in `enforce` mode):
      1. No key → trial banner, full use.
      2. Force trial end → read-only; data readable + exportable.
      3. Install Basic key for the org's tax ID → active; CRM/workflows hidden; 2nd branch refused.
      4. Install Integrated renewal (same `license_id`) → CRM back, branch limit 5.
      5. Maintenance ended + newer `RELEASE_DATE` → `upgrade` refused before migrate; renewal lifts it.
      6. Change org VAT → company mismatch → e-invoice submit refused; prints show licensed identity.
      7. AI add-on expired → assistant hidden; ASSISTANT still configured.
- [ ] **`Docs/RUNBOOK.md`** — new section "License keys": install, status, renew, what each banner
      means, what to do if the customer changes their tax ID (re-issue, `--replace-company`).
- [ ] **`Docs/sales/LICENSE_ISSUING.md`** (founder-only procedure): generate keypair once, where the
      private key lives + offline backup, issuing a key after payment, renewal, lost-key policy,
      edition table with current prices (from the founder's price decision), and the honest
      anti-copy statement (binding + LICENSE terms, not DRM).
- [ ] **`DECISIONS.md`** entry "Perpetual license key" — the 8 locked decisions + why no machine
      fingerprint + why no phone-home.
- [ ] **Gates:** full `pytest`, `gate:all`, i18n parity, `tsc -b`.

## Smoke test
- [ ] All 7 drive steps pass, recorded with date + result in this file.
- [ ] A second person (or fresh session) can issue + install a key using only `LICENSE_ISSUING.md`.

## After This Session
Commit `docs(licensing): acceptance + runbook + issuing procedure (license-key FILE_06)`,
rename `_done`, **merge to main** (gates green first), mark the plan closed in
`EXECUTION_ORDER.md`, update `erp-status`.
