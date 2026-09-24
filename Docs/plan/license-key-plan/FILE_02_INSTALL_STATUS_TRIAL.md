# FILE_02 — Install, status, provisioning hook, trial state, license API

**Model: Sonnet.** **Effort: Small–Medium.**

## Goal
An operator can install a key, see its status, and a fresh install without a key runs a 30-day
trial. Still no enforcement — this file only computes and stores the state.

## Before You Start
- `FILE_01_*_done.md` (verifier API).
- `erp/core/management/commands/provision_customer.py` — add the license step without breaking
  its "cannot produce an unsafe install" promise; `--verify` must report license state.
- `erp/identity/models.py` `OrgPreferences` — where `vat_number` / `company_name` live.

## Tasks
- [ ] **Model `InstalledLicense`** (single row, pk=1): `key_text`, `installed_at`,
      `installed_by`, `first_run_at` (trial start, set once on first boot/migrate),
      `last_seen_date` (for clock-rollback detection in FILE_03).
- [ ] **`services/state.py`** — `current_state() -> LicenseState`, cached per request, one of:
      `unmanaged` (LICENSE_MODE=off) · `trial` (days_left) · `trial_ended` · `active` ·
      `invalid` (verify failed) · `company_mismatch` (tax ID ≠ `OrgPreferences.vat_number`).
      Plus derived flags: `maintenance_active`, `maintenance_until`, `ai_active`, `modules`,
      `max_branches`. Tax IDs compared after normalising spaces/dashes.
- [ ] **Commands:** `manage.py license install <file-or-key>` (verify first; refuse invalid with a
      clear reason; audit-logged), `manage.py license status` (human summary, ar-friendly text in
      output is fine as English — it's an operator tool).
- [ ] **`provision_customer --license-file PATH`** — installs during go-live; the go-live report
      and `--verify` print the license line. Without the flag: warn ("running as trial"), don't fail.
- [ ] **API** `GET /api/license/` (any signed-in user: state + edition + dates — no key text) and
      `POST /api/license/` (System Admin only: paste a key). Server-side verify; never trust
      client-sent fields.
- [ ] **Tests:** each state reachable; trial day math at boundaries (day 30 vs 31); mismatch when
      the org VAT is changed after install; POST by a non-admin → 403; invalid key → 400 with the
      typed reason; GET never exposes `key_text`.

## Smoke test
- [ ] `pytest erp/licensing erp/core` green.
- [ ] Dev DB with `LICENSE_MODE=enforce`: `license status` → trial, 30 days left. Install a test
      key issued for the dev org's VAT → `active`. Change org VAT → `company_mismatch`.
- [ ] `LICENSE_MODE=off` → `unmanaged`, full suite green.

## After This Session
Commit `feat(licensing): install/status commands, trial state, license API (license-key FILE_02)`,
rename `_done`, update `erp-status`.
