# FILE_05 — Archiving + acceptance  (Medium)

## Goal
Close the compliance loop: durable long-term archiving of issued/valid e-invoices (ETA requires
retention), a credential-gated real-sandbox smoke in gate10, and a written acceptance that live
e-invoicing works end to end. This file flips `pre-handover-hardening/FILE_01` Branch A to satisfied.

## Before you start (read)
- `erp/einvoice/domain/models.py` (`ETAInvoice` as the record), `services/issue.py`
- `scripts/gates/gate10.py` (extend, don't rewrite)
- ETA retention requirements (look up — cite the retention period + format)

## Tasks
- [ ] Persist the full signed document + ETA response (UUID, long-id, status) durably — retrievable
      for the required retention window. Confirm whether the `ETAInvoice` row + audit suffices or a
      document blob store is needed; implement the gap.
- [ ] Add a retrieval/export path: given an invoice, produce its official ETA document + status for
      audit/tax review.
- [ ] Extend `gate10` with an opt-in (credential-gated, skipped without creds) real-sandbox smoke:
      submit → sign → valid → archived. Offline/no-creds runs still pass on the existing simulated
      path so CI stays green.
- [ ] Acceptance: run one full real-sandbox order→invoice→submit→valid→archive; record the result +
      screenshots in a `_done` note; update `DECISIONS.md`; if Branch A, mark handover-blocker
      cleared.

## Watch
- CI must not require ETA creds — the real smoke is opt-in; the simulated path remains the default
  gate10 check so `pre-handover-hardening/FILE_02` CI stays green.

## Done when
An issued invoice is signed, accepted (`valid`) by the ETA sandbox, and archived retrievably; gate10
covers both simulated (default) and real-sandbox (opt-in) paths; acceptance recorded. Real ETA
e-invoicing is proven end to end.

## How to test
- With sandbox creds: `gate10` real smoke → submit→valid→archive passes; retrieval returns the
  official document.
- Without creds: `gate10` passes on the simulated path (CI unaffected).
- Acceptance note + DECISIONS entry present.
