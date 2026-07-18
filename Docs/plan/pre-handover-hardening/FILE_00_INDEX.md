# Pre-Handover Hardening — Master Index

> **Source: QA/handover audit, 2026-07-18.** This plan = the audit's Phase 0 "Must-Have before
> handover" set. It runs BEFORE the customer handover gate
> (`Docs/plan/delivery-readiness/FILE_07_HANDOVER_GATE.md` sections C/D/E). Nothing here is
> optional for go-live; each file closes one Critical/High audit finding.

## Why this plan exists

The app itself is well-built and E2E-verified (1,415 backend tests, 4 passing delivery drives).
The audit found **no product-logic blockers** — the blockers are around the product: a compliance
disclosure, a missing CI safety net, a missing frontend crash guard, and handover hygiene. All are
Small–Medium effort. This plan clears them so the on-site handover in delivery-readiness FILE_07
can proceed honestly.

## The files (strict order; one file = one session)

| File | Task | Sev closed | Effort | Model |
|---|---|---|---|---|
| FILE_01 | ETA e-invoicing decision + disclosure | 🔴 Critical | Small | Opus (judgment) |
| FILE_02 | CI safety net (gates + pytest + web checks on push/PR) | 🟠 High | Small–Med | Sonnet |
| FILE_03 | Top-level React error boundary + designed fallback | 🟠 High | Small | Sonnet |
| FILE_04 | Fresh full gate run → dated artifact in handover package | 🟠 High | Small | Haiku/Sonnet |
| FILE_05 | LICENSE file + support/warranty terms note | 🟡 Med | Small | Haiku |
| FILE_06 | Loose ends: canvas smoke, partial-pay Q, delete test user | 🟡 Med | Small | Sonnet |

## Locked decisions (re-confirm only if code contradicts)

1. **FILE_01 is a founder decision, not a code task.** Two branches: (a) real ETA integration
   → triggers `Docs/plan/einvoice-eta-live/` as a Must-Have blocker; (b) documented simulation +
   written customer sign-off + interim manual-filing procedure. Either closes the finding; the
   founder picks. This file's output GATES whether the invoice plan blocks handover.
2. **CI mirrors the local gate harness — it does not replace it.** FILE_02 wires
   `scripts/gates/_run.py all` + `pytest` + `apps/web` typecheck/i18n-parity into GitHub Actions.
   No new quality logic; just automation of what already runs locally.
3. **The error boundary is on-brand, not a stack trace.** FILE_03's fallback is a designed,
   bilingual, monochrome "something went wrong — reload" state per the Conductor Standard, not a
   raw React error screen.
4. **No new runtime dependencies** without a DECISIONS entry first (team rule 7). CI actions and a
   dev-only lint tool are not runtime deps.

## Exit = handover-ready

When all six are `_done`: the audit's Phase 0 is closed → proceed to delivery-readiness FILE_07
sections C/D/E (on the real customer machine, founder + customer present).

## Change log
- **2026-07-18 — Created** from the pre-handover QA audit. Inserted into `EXECUTION_ORDER.md` as
  the new pos 8-A (ahead of the delivery-readiness FILE_07 handover gate).
