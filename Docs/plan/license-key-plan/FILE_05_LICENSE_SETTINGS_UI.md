# FILE_05 — Settings → License page + calm status banners (ar/en)

**Model: Sonnet.** **Effort: Small–Medium.** UI session → `conductor-brand` + `erp-frontend` first.

## Goal
The owner sees, in plain Arabic, what they bought, until when updates are covered, and how to
renew — and is told early and calmly, never ambushed.

## Before You Start
- Recall `ag-ui-standard`, `conductor-brand`, `erp-frontend`.
- Register the four canonical terms in `Docs/Brand/Conductor_Visual_Identity_System.md` §6
  **before** writing keys: ترخيص · الصيانة السنوية · الباقة · فترة التجربة (FILE_00 decision 8).
- An existing Settings page (e.g. `/settings/organization`) to copy layout/primitives from.
- `GET/POST /api/license/` from FILE_02.

## Tasks
- [ ] **`/settings/license`** (System Admin edits; others read): company + tax ID from the key,
      package, included modules, branch allowance ("unlimited users" stated plainly), maintenance
      end date, AI add-on end date, "paste a new key" field + one primary action.
- [ ] **Banner states** (one quiet line under the page header bar, token colours, colour always
      paired with a word/icon, dismissible per session except read-only):
      trial (N days left) · maintenance ends in ≤ 30 days · maintenance ended (info, not warning —
      the app still works) · read-only (trial ended / invalid / company mismatch / unlicensed
      release) with the exact fix. Blame-free copy: "الصيانة السنوية انتهت — برنامجك شغال عادي،
      والتجديد بيرجعلك التحديثات."
- [ ] **Read-only UX:** save buttons disabled with the reason on hover/focus; a 403
      `license_read_only` / `module_not_licensed` from the API shows the designed message, never a
      raw error toast.
- [ ] **Every state designed** (loading skeleton, invalid-key inline error, success toast).
- [ ] i18n keys in BOTH `ar.json` and `en.json`; logical CSS only; tokens only.

## Smoke test
- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc -b` + `python scripts/gates/gate03.py` green.
- [ ] Live, `enforce` mode, ar + en, light + dark: trial banner → paste a valid key → active page;
      paste a garbage key → inline typed error; maintenance-ending banner with a test key ending in
      10 days; read-only state disables saves with the reason. Screenshot each for the PR.
- [ ] Brand-feel checklist (conductor-brand) passes.

## After This Session
Commit `feat(licensing): Settings → License page + status banners (license-key FILE_05)`,
rename `_done`, update `erp-status`.
