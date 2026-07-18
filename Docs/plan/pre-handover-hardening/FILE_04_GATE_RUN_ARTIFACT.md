# FILE_04 — Fresh full gate run → dated artifact  🟠 High

## The finding
The audit found **no persisted proof** that gates actually pass — only commit messages and
`DECISIONS.md` prose. "Gates green" is an unverified claim until a fresh run is captured. The
handover package should carry evidence, not narrative.

## Before you start (read)
- `scripts/gates/_run.py`
- `Docs/plan/delivery-readiness/FILE_02_HANDOVER_GUIDE.md` (where the package lives)
- `erp-status` skill env facts (venv, DB, Redis start commands)

## Tasks
- [ ] Ensure Postgres + Redis up (`Get-Service`, `redis-cli ping` → PONG).
- [ ] Run `.\.venv\Scripts\python.exe scripts\gates\_run.py all`, capturing full stdout to
      `Docs/plan/delivery-readiness/gate-runs/gate-all-YYYY-MM-DD.log`.
- [ ] Run `apps/web` checks (`node scripts/check-i18n-parity.mjs`, `npx tsc -b`) and append their
      output to the same dated log.
- [ ] If ANY gate fails: stop, fix root cause in the current session (do not `_done` this file with
      a red gate), re-run, then capture the green log.
- [ ] Reference the log file from `FILE_02_HANDOVER_GUIDE.md`.

## Watch
- Once FILE_02 (CI) lands, CI produces this proof automatically per push — this file is the
  one-time captured baseline for the handover package; the CI run is the ongoing proof.
- Do not commit secrets — the log is gate output only; scan it before committing.

## Done when
A dated `gate-all-*.log` showing every gate PASSED (00–17) + web checks is committed under
`delivery-readiness/gate-runs/` and linked from the handover guide.

## How to test
- Open the log → last lines show all gates PASSED, tsc clean, i18n parity OK.
- File is referenced in `FILE_02_HANDOVER_GUIDE.md`.
