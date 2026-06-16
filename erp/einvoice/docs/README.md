# E-Invoicing (ETA)

Compliance module that records every posted sales invoice as an **ETA e-invoice** and runs the
Egyptian Tax Authority submission lifecycle: `draft → submitted → valid` (or `rejected`).

- **Event-driven, decoupled.** It subscribes to the `sales.OrderInvoiced` domain event (enriched with
  the invoice's business data) and records a draft `ETAInvoice`. Sales has no knowledge of this
  module; the only link is the public event name + payload. Subscriber failures are isolated by the
  bus and never break invoicing.
- **References by business key.** The record holds `invoice_number` / `customer_code` / totals — no FK
  crosses the module boundary.
- **Stubbed ETA adapter** (`services/eta_adapter.py`): the real ETA API needs signing + credentials +
  network, out of scope for an offline/customer-hosted build. The stub is deterministic — `submit`
  returns a stable UUID derived from the document hash (idempotent retries, reproducible tests) and
  `query` validates the document. Swapping in a real HTTP client only touches that file.

API: `/api/einvoice/invoices` (list), `/invoices/{id}` (detail), `/invoices/{id}/submit`,
`/invoices/{id}/poll`. Gate: `gate10`.
