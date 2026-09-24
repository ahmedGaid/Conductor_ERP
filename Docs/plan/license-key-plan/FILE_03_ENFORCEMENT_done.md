# FILE_03 — Enforcement: modules, branches, AI add-on, company binding, read-only

**Model: Sonnet**, with an **Opus review of the read-only guard** before commit.
**Effort: Medium.** Merge checkpoint after this file.

## Goal
The license state from FILE_02 actually shapes the app — in `enforce` mode only — without ever
locking a customer out of reading or exporting their own data.

## Before You Start
- `FILE_00_INDEX.md` decisions 4–8 (binding, unlimited users, AI add-on, calm states).
- `FILE_02_*_done.md` (`current_state()`).
- The permission layer that consumes `erp/identity/rbac.py` codes, and the frontend nav registry —
  find both with `codegraph_explore` first; unlicensed modules hide through the SAME path RBAC
  already uses, not a second parallel mechanism.
- `erp/core/models.py` `Branch` + its create service.
- `erp/assistant/client.py` `enabled()`.
- The e-invoice submission service (`erp/einvoice/`) and the document/print header that shows the
  company tax ID.

## Tasks
- [ ] **Modules:** a module not in `state.modules` → its API returns 403 with a typed
      `module_not_licensed` error, and it disappears from nav/⌘K. System Admin sees it as a quiet
      "not in your package" row in Settings (FILE_05), not a broken page.
- [ ] **Branches:** creating a branch beyond `max_branches` → validation error "your package covers
      N branches". Existing branches are never deleted or hidden by a downgrade.
- [ ] **AI add-on:** effective assistant on = existing `enabled()` AND `state.ai_active`. When off,
      the assistant surfaces are hidden the same way `ASSISTANT_ENABLED=False` already hides them.
- [ ] **Company binding:** in `company_mismatch`, e-invoice submission refuses (typed error) and
      printed documents show the **licensed** company name/tax ID from the key.
- [ ] **Read-only guard** for `trial_ended` / `invalid` / `company_mismatch`: middleware rejects
      writes (POST/PUT/PATCH/DELETE) with a typed `license_read_only` error **except** the license
      endpoints, sign-in/out, and exports/prints. All reads + exports keep working. (Opus reviews
      this list — a wrong allowlist either locks data or leaks writes.)
- [ ] **Clock rollback:** if today < `last_seen_date` by more than 2 days, record an audit event and
      flag the state; never lock on it alone (clocks drift on real servers).
- [ ] **`LICENSE_MODE=off` short-circuits every check above** — one early return per check.
- [ ] **Tests:** each gate in `enforce` vs `off`; read-only still allows GET + export + license POST;
      branch limit at N and N+1; AI hidden when `ai_until` passed; mismatch blocks e-invoice submit.

## Smoke test
- [ ] `pytest` full suite green (with default `off`).
- [ ] `LICENSE_MODE=enforce` on the dev DB with a **Basic** test key: CRM + workflows gone from nav,
      `/api/crm/...` → 403 typed; 2nd branch creation refused; trial-ended DB: every list page opens,
      CSV export works, "new order" save refused with the calm message.

## After This Session
Commit `feat(licensing): enforce modules/branches/AI/binding + read-only guard (license-key FILE_03)`,
rename `_done`, **merge checkpoint** (gates green first), update `erp-status`.
