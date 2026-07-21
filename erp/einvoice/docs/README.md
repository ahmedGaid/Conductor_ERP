# E-Invoicing (ETA)

Compliance module that records every posted sales invoice as an **ETA e-invoice** and runs the
submission lifecycle: `draft → submitted` (prepared) `→ valid` (or `rejected`).

> **Reaches the Tax Authority only when configured.** The adapter has two modes behind one
> interface: **simulated** (default — `eta_adapter.is_live()` is False when ETA is not configured or
> has no API base URL) where `poll` returns `pending`, `valid` is unreachable, and `uuid` holds a
> **locally generated reference**; and **live** (FILE_02 — credentials + API base present) where
> `submit` POSTs a real ETA Invoice v1.0 document and `uuid`/`long_id` are ETA-assigned. The UI, help
> and glossary hedge in both languages while simulated. **Still STOP-gated for a validating live
> submission:** the company tax profile (issuer name/activity/address via `ETA_ISSUER_*`) and the
> customer's tax registration, plus document signing (FILE_03). When those land, remove the
> `einvoice.notConnected` note from `EInvoicesPage.tsx` and un-hedge the copy listed in DECISIONS.md
> (2026-07-20 claims-discipline entry).

- **Event-driven, decoupled.** It subscribes to the `sales.OrderInvoiced` domain event (enriched with
  the invoice's business data) and records a draft `ETAInvoice`. Sales has no knowledge of this
  module; the only link is the public event name + payload. Subscriber failures are isolated by the
  bus and never break invoicing.
- **References by business key.** The record holds `invoice_number` / `customer_code` / totals — no FK
  crosses the module boundary.
- **Stubbed ETA adapter** (`services/eta_adapter.py`): the real ETA API needs signing + credentials +
  network, out of scope for an offline/customer-hosted build. The stub is deterministic — `submit`
  returns a stable local reference derived from the document hash (idempotent retries, reproducible
  tests) and `query` returns `pending`, never a verdict it did not receive. Swapping in a real HTTP
  client only touches that file.

API: `/api/einvoice/invoices` (list), `/invoices/{id}` (detail), `/invoices/{id}/submit`,
`/invoices/{id}/poll`. Gate: `gate10`.
