# FILE_07 — HANDOVER GATE (final pre-handover checklist — nothing ships to a customer before every box is checked)

This gate closes the delivery-readiness program. It is run TWICE: once on the dev box (dry
run), once on the REAL customer machine (the one that counts). FILE_04_SIGNOFF_CHECKLIST is a
component of this gate, not a substitute.

---

## A. Build prerequisites (Claude sessions — all must be `_done`)

- [ ] `FILE_05_PARTIAL_PAYMENTS` — partial collect/pay in the UI, ledger-verified
- [ ] `FILE_06_PROVISIONING` — `provision_customer` command + `--verify`
- [ ] `twenty-harvest FILE_01` — release versioning (VERSION/CHANGELOG/tag, version visible)
- [ ] `twenty-harvest FILE_02` — `manage.py upgrade` (idempotent, recorded, post-checked)
- [ ] `twenty-harvest FILE_03` — gate16 upgrade drill + gate17 API snapshot, wired into gate:all

## B. Verification on the dev box (Claude + founder)

- [x] `python scripts/gates/_run.py all` green (now incl. 16/17) — 2026-07-18, gates 00-17 PASSED
- [x] Delivery E2E drives re-pass after FILE_05 changes (sales + purchasing flows especially) —
      2026-07-18: found+fixed a dev-DB migration gap (`sales.0008/0009`, `inventory.0007/0008`,
      `purchasing.0008`, `core.0003/0004` were unapplied on the `erp` dev DB, causing 500s on
      customers/orders/items — `manage.py migrate` fixed it; this is a dev-box-only state issue,
      not a code bug). Then drove fresh order SO-2026-000038 (create→confirm→deliver→invoice→
      partial-collect 100/150 EGP, outstanding→50, DB-verified paid_minor=10000) and PO-2026-000002
      partial-pay (800/2000 EGP, outstanding→1200). Trial balance Dr=Cr=214,469,476 post-drive. PASS.
- [ ] Workflow canvas 2-minute HUMAN smoke test (mouse drag node→node, Save, Run) — the one
      thing headless E2E could not exercise (FILE_03 known issue). **Not verifiable by a Claude
      browser-pane session**: the pane tab runs backgrounded (`document.visibilityState ===
      'hidden'`), which suspends the rAF-gated code React Flow uses to flip nodes from
      `visibility:hidden` to visible after measurement — nodes never render, so no genuine mouse
      interaction is possible here. Needs a human at a real foreground browser.
- [ ] Partial-payments question ASKED to the customer; answer recorded here: __________

## C. On the REAL customer machine (founder, with the customer)

- [ ] OS/PG16/Redis installed per RUNBOOK; `.env` written (real secrets, no dev values)
- [ ] `manage.py provision_customer` → all-green report; admin password set by the CUSTOMER
- [ ] `provision_customer --verify` green (zero demo users, no known passwords, empty books)
- [ ] `FILE_04_SIGNOFF_CHECKLIST` executed on THIS machine, every line
- [ ] Backup taken per RUNBOOK **and restored** to a scratch DB on this machine (restore drill
      — a backup that never restored is not a backup)
- [ ] Version + upgrade dry-run: `manage.py upgrade --yes` no-op clean on the live install

## D. First live actions (day one, customer present)

- [ ] **ETA e-invoice**: customer's real/sandbox credentials in `.env` → submit ONE invoice
      end-to-end → accepted. This is the first live action, before real sales volume. FAIL →
      customer keeps their old invoicing channel until fixed; not silently deferred.
- [ ] First real customer + item + invoice + (partial) collection entered by THEIR clerk, not
      by us — watch, don't drive
- [ ] Trial balance checked at end of day one

## E. Standing arrangements (agree before leaving)

- [ ] Backup cadence scheduled (RUNBOOK) + who checks it weekly: __________
- [ ] Update channel: founder applies releases via `manage.py upgrade` (never manual SQL)
- [ ] Known-issues list (FILE_03) handed over and acknowledged: partial features, AI off,
      smart-import deferred
- [ ] Support contact + response expectation written down

## Sign-off

Dev dry run: date ______ by ______   ·   Customer machine: date ______ by ______
Customer acknowledgement: ______

```
All boxes checked on the customer machine?
→ Rename with _done. Update erp-status (delivery program CLOSED; queue resumes at twenty-harvest FILE_04).
```
