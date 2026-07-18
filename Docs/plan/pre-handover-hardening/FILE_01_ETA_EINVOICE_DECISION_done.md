# FILE_01 — ETA e-invoicing: decision + disclosure  🔴 Critical

## The finding (audit 2026-07-18)

`erp/einvoice/services/eta_adapter.py` is a **simulated stub** — its own docstring says so.
`submit()` returns a UUID derived from a SHA-256 of the document; "signing" is a hash, not a real
ETA cryptographic signature. `gate10.py` passing proves the *lifecycle* (draft→submitted→valid),
NOT a real government submission. Egyptian ETA e-invoicing is a **legal VAT obligation**. If the
customer assumes gate-green = compliant, they operate believing invoices reached ETA when none did.

## Before you start (read)
- `erp/einvoice/services/eta_adapter.py` (the stub + its docstring)
- `erp/einvoice/services/issue.py` (record → submit → poll lifecycle)
- `erp/einvoice/docs/README.md`
- Brief §12 (claims discipline) — do not market e-invoicing beyond what ships

## This is a founder decision, not a code change

The session's job is to surface the two branches cleanly and record the founder's pick in
`DECISIONS.md`, then execute the disclosure path (if chosen). Ask the founder:

**Branch A — real ETA integration before handover.**
Customer needs live compliant e-invoicing on day one. → This makes
`Docs/plan/einvoice-eta-live/` a **Must-Have handover blocker**. Do NOT hand over until it's
`_done`. (Requires ETA production/sandbox credentials + tax profile from the customer.)

**Branch B — ship with documented simulation + sign-off.**
Customer files VAT another way at first, or e-invoicing is phased in post-handover. → Deliver:
1. A one-page written disclosure (Arabic + English) stating e-invoicing submission is currently
   simulated / not yet connected to the live ETA portal, added to the handover package.
2. A written, founder-countersigned customer acknowledgement line in
   `delivery-readiness/FILE_04_SIGNOFF_CHECKLIST.md`.
3. An interim manual-filing note in `delivery-readiness/FILE_03_KNOWN_ISSUES.md`.

## Tasks
- [ ] Present both branches to the founder in one message; get the pick.
- [ ] Record the decision + reasoning in `DECISIONS.md` (dated).
- [ ] If Branch A: mark `einvoice-eta-live` as Must-Have blocker in `EXECUTION_ORDER.md` and stop
      (that plan is the next work).
- [ ] If Branch B: write the bilingual disclosure page, add the sign-off line, add the known-issue
      note. Verify the app UI does not *claim* live ETA submission anywhere (grep `apps/web` locales
      for e-invoice status strings; soften any that imply live government submission).

## Done when
Founder decision recorded in `DECISIONS.md`; either the invoice plan is flagged as a blocker
(Branch A) or the disclosure + sign-off + known-issue + UI-copy check are all in place (Branch B).
No user-facing string implies compliant live submission that isn't real.

## How to test
- Branch B: open the handover package — disclosure page present in both languages.
- Search `apps/web/src/locales` for e-invoice status strings → none asserts "submitted to the Tax
  Authority" as a completed live fact.
- `DECISIONS.md` has the dated entry.
