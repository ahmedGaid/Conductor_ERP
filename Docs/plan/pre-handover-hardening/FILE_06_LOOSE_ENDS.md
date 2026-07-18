# FILE_06 — Handover loose ends  🟡 Medium

## The findings (small, tracked, not yet closed)
Three items already flagged in `erp-status` / delivery-readiness FILE_07 section B that a human/
session must close before go-live:
1. **Workflow canvas smoke** — drag-and-drop can't be verified from a backgrounded automation
   browser (React Flow rAF-gated). Needs a 2-minute test at a real foreground browser.
2. **Partial-payments policy question** — not yet asked of the customer (FILE_07 section B blank).
3. **Dev test user `phase1d_qa`** — must be suspended/deleted before handover (erp-status TODO).

## Tasks
- [ ] Founder (or session driver on a real foreground browser): open `/workflows/new`, drag two
      nodes, connect them, save, reload → nodes + edge persist. Record pass in FILE_07 section B.
- [ ] Ask the customer the partial-payments policy question; record the answer in FILE_07 section B.
      (Partial-payments UI already shipped — `delivery-readiness/FILE_05_PARTIAL_PAYMENTS_done.md`;
      this is just confirming the customer's expected behavior.)
- [ ] Suspend or delete user `phase1d_qa` in the dev DB (and confirm it never existed on the
      customer machine's fresh provision).
- [ ] Tick the corresponding boxes in `FILE_07_HANDOVER_GATE.md` section B.

## Watch
- The canvas smoke is the ONE item repeatedly flagged as un-automatable — do not mark it done from a
  headless/backgrounded session; it needs real human eyes on a foreground tab.

## Done when
FILE_07 section B canvas + partial-payments boxes are checked with recorded results; `phase1d_qa`
is gone from any DB that could ship.

## How to test
- FILE_07 section B shows both boxes checked with a date + result.
- Query the dev DB users → `phase1d_qa` absent or suspended.
