# FILE_05 — README cross-platform + Django 6 deprecation

## Findings
1. `README.md` covers Windows install only (winget + PowerShell). No Linux/macOS path — a problem
   if the customer or a future maintainer runs anything but Windows.
2. `pytest` surfaces `RemovedInDjango60Warning` at `erp/accounting/domain/models.py:394`
   (`CheckConstraint.check` deprecated in favor of `.condition`). Trivial now; blocks a future
   Django 6 upgrade.

## Tasks
- [x] Add Linux + macOS prerequisites/quickstart to `README.md` (Postgres 16, Redis, Python 3.13,
      Node 24 install per-OS; the manage/seed commands are already cross-platform). — done 2026-07-19
- [x] Fix `CheckConstraint(check=...)` → `condition=...` at `erp/accounting/domain/models.py:389,394`
      (grepped repo-wide — only these two usages; migrations already serialize as `condition=`, so
      `makemigrations --check --dry-run accounting` confirms no new migration needed).
- [x] Confirm no new deprecation warnings introduced; `pytest erp/accounting -W error::DeprecationWarning`
      → 80 passed, no warning raised.

## Done when
README has all three OS install paths; the CheckConstraint deprecation is gone; accounting tests
green with no `RemovedInDjango60Warning`.

## How to test
- `pytest erp/accounting` → no deprecation warning in output.
- README renders Linux/macOS/Windows sections.

## Closed 2026-07-19 (A, `C:\AhmedGaid\ERP`)
Both findings fixed; no new deps, no browser needed — ran ahead of the "after handover" sequencing
note in `FILE_00_INDEX.md` since neither change is customer-facing or risky pre-handover.
