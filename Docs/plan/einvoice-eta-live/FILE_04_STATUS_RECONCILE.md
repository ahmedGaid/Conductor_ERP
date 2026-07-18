# FILE_04 — Status reconciliation  (Medium)

## Goal
ETA validation is asynchronous. Replace the stub `poll_invoice` with a real reconciliation loop
that queries ETA for each submitted invoice, maps `valid`/`rejected`/`cancelled` to `ETAInvoice`
states, retries transient failures, and surfaces final status in the UI.

## Before you start (read)
- `erp/einvoice/services/issue.py` (`poll_invoice`), `domain/models.py` states
- FILE_02 response mapping; `config/settings/base.py` Celery/beat config
- ETA status-query endpoint (look up — cite)

## Tasks
- [ ] `poll_invoice` (or a Celery task) queries ETA per submitted invoice; update state atomically
      + `audit.record`.
- [ ] Retry/backoff for transient ETA errors; cap retries; a stuck invoice raises an operator-
      visible alert (not a silent hang).
- [ ] Schedule the reconcile task on the existing Celery beat (mirror the hourly report sweep).
- [ ] `/einvoice` UI reflects live status (valid/rejected/pending) with human, blame-free copy.

## Watch
- Idempotent polling — polling an already-`valid` invoice is a no-op.
- Don't hammer ETA — respect rate limits; backoff.

## Done when
Submitted sandbox invoices auto-progress to `valid`/`rejected` without manual poking; transient
failures retry then alert; UI shows current status. `pytest erp/einvoice` + gate10 green.

## How to test
- Submit sandbox invoices → beat task advances them to final state within its interval.
- Simulate a transient ETA error → retries, then alerts, no crash.
