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

- [ ] `python scripts/gates/_run.py all` green (now incl. 16/17)
- [ ] Delivery E2E drives re-pass after FILE_05 changes (sales + purchasing flows especially)
- [ ] Workflow canvas 2-minute HUMAN smoke test (mouse drag node→node, Save, Run) — the one
      thing headless E2E could not exercise (FILE_03 known issue)
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
