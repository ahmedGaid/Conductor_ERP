# E-Invoicing (ETA)

Compliance module that records every posted sales invoice as an **ETA e-invoice** and runs the
submission lifecycle: `draft → submitted` (prepared) `→ valid` (or `rejected`).

> **Nothing here reaches the Tax Authority yet.** The adapter is simulated
> (`eta_adapter.SIMULATED = True`), so `poll` returns `pending` and `valid` is unreachable; the
> `uuid` field holds a **locally generated reference**, not an ETA UUID. The UI, help content and
> glossary say so in both languages. When a real adapter lands (`einvoice-eta-live` FILE_02+), flip
> `SIMULATED`, and in the same change remove the `einvoice.notConnected` note from
> `EInvoicesPage.tsx` and un-hedge the copy listed in DECISIONS.md (2026-07-20 claims-discipline
> entry).

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
