# FILE_05 — README cross-platform + Django 6 deprecation

## Findings
1. `README.md` covers Windows install only (winget + PowerShell). No Linux/macOS path — a problem
   if the customer or a future maintainer runs anything but Windows.
2. `pytest` surfaces `RemovedInDjango60Warning` at `erp/accounting/domain/models.py:394`
   (`CheckConstraint.check` deprecated in favor of `.condition`). Trivial now; blocks a future
   Django 6 upgrade.

## Tasks
- [ ] Add Linux + macOS prerequisites/quickstart to `README.md` (Postgres 16, Redis, Python 3.13,
      Node 24 install per-OS; the manage/seed commands are already cross-platform).
- [ ] Fix `CheckConstraint(check=...)` → `condition=...` at `erp/accounting/domain/models.py:394`
      (and grep for any other `CheckConstraint.check` usages).
- [ ] Confirm no new deprecation warnings introduced; `pytest erp/accounting` green.

## Done when
README has all three OS install paths; the CheckConstraint deprecation is gone; accounting tests
green with no `RemovedInDjango60Warning`.

## How to test
- `pytest erp/accounting` → no deprecation warning in output.
- README renders Linux/macOS/Windows sections.
