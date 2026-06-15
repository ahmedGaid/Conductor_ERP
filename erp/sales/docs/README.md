# Sales & Customers module

Order-to-cash (Stage 5d). Customer priority #3. The clearest cross-module flow in the system: it
drives **Inventory** (issue stock on delivery) and **Accounting** (COGS, AR, revenue, cash) entirely
through their public contracts — never their ORM.

## Layout
- `domain/models.py` — Customer, SalesOrder, SalesOrderLine. Items are referenced by **SKU string**
  (no FK into inventory); warehouse by **code string**.
- `services/orders.py` — the order lifecycle (the orchestration point).
- `contracts/` — order services + event names for other modules.
- `events.py` — `sales.OrderConfirmed/OrderDelivered/OrderInvoiced/PaymentReceived`.
- `api/` — DRF endpoints under `/api/sales/`.

## Lifecycle & GL
`draft → confirm → deliver → invoice → payment` (or `cancelled`). Each transition is atomic + guarded.
- **confirm** — enforces the customer credit limit (outstanding + this order ≤ limit; 0 = unlimited).
- **deliver** — `inventory.contracts.issue(sku, warehouse, qty)` per line → reduces stock and posts
  **Dr COGS / Cr Inventory** at weighted-average cost. Insufficient stock aborts the whole delivery.
- **invoice** — `accounting.contracts.post_journal` **Dr AR (1100) / Cr Sales Revenue (4000)**.
- **payment** — **Dr Cash (1000) / Cr AR (1100)**; full settlement marks the order `paid`.

## Invariants (proven by `tests/`)
1. A full draft→paid flow leaves the **trial balance balanced** and AR back at zero.
2. Delivery reduces inventory and the **Inventory GL still equals stock value**; COGS is posted.
3. Confirm is blocked when it would breach the credit limit (`SAL-002`); nothing changes.
4. Delivering more than on-hand is rejected (via inventory `INV-001`); the order stays confirmed.
5. Over-payment is rejected (`SAL-005`).

## Next slices
Quotations, partial deliveries/invoices, discounts, multi-currency + FX, VAT on invoices (with the
accounting tax slice), and sales-rep commissions.
