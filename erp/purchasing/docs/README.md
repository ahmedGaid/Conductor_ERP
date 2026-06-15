# Purchasing & Suppliers module

Procure-to-pay (Stage 5e). Customer priority #4. Mirror of Sales; it **closes the GRNI loop** that
inventory receipts open. Drives Inventory + Accounting only through their public contracts.

## Lifecycle & GL
`draft → confirm → receive → bill → payment` (or `cancelled`).
- **receive (GRN)** — `inventory.contracts.receive(sku, warehouse, qty, unit_cost)` per line →
  raises stock and posts **Dr Inventory (1200) / Cr GRNI (2150)**. Supports partial receipts.
- **bill** — **3-way match** first (received qty must equal ordered qty per line; `PUR-002` otherwise),
  then `accounting.contracts.post_journal` **Dr GRNI (2150) / Cr Accounts Payable (2000)** — clearing
  the GRNI the receipt created and booking the real payable.
- **payment** — **Dr AP (2000) / Cr Cash (1000)**; full settlement marks the PO `paid`.

Net effect across receive+bill: GRNI returns to zero, value lands in Inventory + AP — exactly the
double entry a vendor purchase should produce.

## Invariants (proven by `tests/`)
1. A full draft→paid flow leaves the **trial balance balanced** and **GRNI back at zero**.
2. Receiving raises inventory and the **Inventory GL still equals stock value**.
3. Billing is blocked by the 3-way match when received ≠ ordered (`PUR-002`); nothing posts.
4. Over-payment is rejected (`PUR-005`); each transition is atomic + guarded (`PUR-001`).

## Next slices
Purchase requisitions (PR) + approval matrix, RFQ/comparison, partial billing, supplier rating,
landed costs, and clearing GRNI per-line on partial receipts.
