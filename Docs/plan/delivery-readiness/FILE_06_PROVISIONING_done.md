# SESSION — Customer Provisioning Command (pre-handover blocker #2)
# Files: erp/core/management/commands/provision_customer.py (new), seed_identity flag check, erp/core/tests/, Docs/RUNBOOK.md

Why blocking: FILE_03 lists the go-live chores as MANUAL steps (fresh DB only, never clone dev,
delete demo users, rotate the known `Dev12345!` password). Manual steps get skipped under
handover pressure. This session makes a clean go-live ONE command that cannot produce an
unsafe install.

---

## Before You Start

1. Open `erp/identity/management/commands/seed_identity.py` (customer-safe since e316801,
   admin-only by default) → confirm exactly which users/roles it creates today and whether any
   demo users or fixed passwords remain in ANY path.
2. Open `seed_accounting` → confirm it seeds chart-of-accounts only (no transactions).
3. Open `erp/monitoring` system-check + the FILE_01/twenty-harvest version wiring (if landed) →
   the post-provision report reuses them.
4. Open `Docs/RUNBOOK.md` install section → this command replaces its manual sequence.

"Do not write anything yet."

---

## Task A — `manage.py provision_customer`

1. **Refuses a dirty database** (any business row exists → abort with a clear message; no
   `--force` — a dirty DB means a wrong target, full stop).
2. Runs `migrate` → `seed_identity` (admin only, NO demo users — if a demo path exists, this
   command must not trigger it) → `seed_accounting`.
3. **Admin password**: from `--admin-password-env VAR` or interactive prompt (twice). Refuses
   known/weak values (`Dev12345!` hard-blocked, min length 12). Never echoed, never logged.
4. 2FA: prints the TOTP enrolment instruction for the admin's first login (existing flow).
5. Post-checks + printed go-live report: system-check OK, books empty, exactly one default
   price list, zero demo users, version line. Non-zero exit if any check fails.

## Task B — `manage.py provision_customer --verify`

Verification-only mode against an existing install (run on the customer box before sign-off):
all Task-A post-checks + no user with a blocked password (verify by attempting hash check
against the blocklist), Redis reachable, backup location configured-or-warned. This is what
FILE_07's gate calls.

## Task C — Tests + RUNBOOK

Tests: dirty-DB refusal; weak/known password refusal; happy path produces admin-only empty
tenant; `--verify` catches a planted demo user. RUNBOOK "Go-live install" section rewritten to:
create DB → set `.env` → `provision_customer` → done.

---

## Smoke Test

- [ ] Fresh scratch DB → command provisions; report all-green; login works with the new password only
- [ ] Re-run on same DB → refused (dirty)
- [ ] `--admin-password` = `Dev12345!` → refused
- [ ] Planted `phase1d_qa`-style user → `--verify` fails naming it
- [ ] `pytest erp/core erp/identity` green; RUNBOOK section copy-pasteable

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ NEXT: run twenty-harvest FILE_01 → FILE_03 (upgrade story — pre-handover blocking),
  then return to FILE_07_HANDOVER_GATE.md.
```
