# SESSION 2 — Upgrade Command
# Files: erp/core/upgrades/ (new pkg), erp/core/management/commands/upgrade.py (new), erp/core/models.py (AppliedUpgradeStep), erp/core/tests/test_upgrade.py (new), Docs/RUNBOOK.md

Twenty reference: `upgrade` core module + per-version command folders
(`upgrade-version-command/2-16/…`) — every release carries its own ordered, idempotent data
fixes; self-hosters run ONE command. That's exactly what a customer-hosted ERP needs.

---

## Before You Start

1. Open `erp/core/models.py` + an existing migration → match model + migration idiom.
2. Open `erp/monitoring/` system-check service → the upgrade command reuses it as post-check.
3. Open `erp/accounting/` trial-balance service fn → second post-check (books still balance).
4. Read FILE_01's `CONDUCTOR_VERSION` wiring.

"Do not write anything yet."

---

## Task A — Step registry

`erp/core/upgrades/__init__.py`:

```python
@dataclass(frozen=True)
class UpgradeStep:
    version: str      # release that introduced it, e.g. "1.1.0"
    name: str         # unique within version, e.g. "backfill_price_list_default"
    run: Callable[[], None]   # idempotent by contract — safe to re-run

REGISTRY: list[UpgradeStep]  # ordered; steps live in erp/core/upgrades/v1_1_0.py etc.
```

Model `AppliedUpgradeStep(version, name, applied_at)` — unique together (version, name).

## Task B — The command

`manage.py upgrade`:

1. Print current code version (settings) vs DB state; require confirmation unless `--yes`.
2. Remind about backup (`--skip-backup-check` to bypass; RUNBOOK pg_dump section is the law).
3. `call_command("migrate")`.
4. Run REGISTRY steps not yet in `AppliedUpgradeStep`, in order, each in a transaction; record
   on success. Failure → halt with the step name + actionable message (blame-free), nothing
   half-applied.
5. Post-checks: system-check service OK + trial balance balanced. Print a short report.

Re-run when everything applied = clean no-op.

## Task C — Tests

Fake registry with two steps: fresh run applies both + records; second run applies none;
mid-failure halts, first step stays recorded, re-run resumes at the failed step.

---

## Smoke Test

- [ ] `python manage.py upgrade --yes` on the dev DB: migrates, applies 0 pending steps, prints
      version + post-checks OK
- [ ] Re-run → explicit no-op message
- [ ] `pytest erp/core` green
- [ ] RUNBOOK upgrade section: stop app → backup → `upgrade` → start app, copy-pasteable

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_03_UPGRADE_DRILL_GATES.md in a FRESH session.
```
