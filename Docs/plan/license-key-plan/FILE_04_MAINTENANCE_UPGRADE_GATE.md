# FILE_04 — Maintenance gate in `manage.py upgrade` + renewal

**Model: Sonnet.** **Effort: Small.**

## Goal
Annual maintenance means something: a customer whose maintenance ended keeps running their
current version forever, but cannot install a newer release until they renew.

## Before You Start
- `erp/core/management/commands/upgrade.py` — the existing upgrade flow (migrate → registered
  steps → post-checks). The gate goes **before** `migrate`, so a refused upgrade changes nothing.
- `VERSION` + `config/settings/base.py` `APP_VERSION` — how the version is read today.
- `Docs/RUNBOOK.md` "Upgrading to a new release".

## Tasks
- [ ] **Release date:** add `RELEASE_DATE` next to `VERSION` (a `RELEASE_DATE` file, ISO date,
      bumped with every release; setting `APP_RELEASE_DATE` read like `APP_VERSION`).
- [ ] **Gate:** in `enforce` mode, if `RELEASE_DATE > state.maintenance_until` → `CommandError`
      *before* migrating: "This release (1.4.0, 2027-03-01) is newer than your maintenance
      (ended 2027-01-15). Install a renewal key, then run upgrade again." No data touched.
- [ ] **Renewal = a new key** with the same `license_id` + later `maintenance_until`, installed via
      `license install` / Settings. Installing a key with a *different* `tax_id` than the current
      one requires `--replace-company` (guards against pasting another customer's key).
- [ ] **Runtime check too:** on boot, if the running code's `RELEASE_DATE` is after
      `maintenance_until` (someone copied new files without `upgrade`), state gets
      `unlicensed_release` → read-only (same guard as FILE_03), with a message saying exactly
      which renewal fixes it.
- [ ] **Tests:** release before/on/after the date; refused upgrade leaves `AppliedUpgradeStep`
      untouched; renewal key lifts the block; `off` mode never gates.

## Smoke test
- [ ] `pytest erp/licensing erp/core` green.
- [ ] Test key with `maintenance_until` = yesterday + `RELEASE_DATE` = today → `upgrade --yes`
      refuses before migrate; install a renewal key → `upgrade --yes` runs.

## After This Session
Commit `feat(licensing): maintenance gates upgrades + renewal keys (license-key FILE_04)`,
rename `_done`, update `erp-status`. Add the "bump RELEASE_DATE" line to the release checklist.
