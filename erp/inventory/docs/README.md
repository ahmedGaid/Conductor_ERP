# Inventory & Warehouses module

Stock control (Stage 5c). Customer priority #2. Posts to the General Ledger **through the accounting
public contract** (`erp.accounting.contracts.post_journal`) — never via accounting's ORM.

## Layout
- `domain/` — `models.py` (Category, Item, Warehouse, StockBalance, StockMovement), `costing.py`
  (weighted-average helpers, pure functions).
- `repositories/` — typed data access.
- `services/` — `stock.py` (receive/issue/transfer; the invariant point), `reports.py` (on-hand).
- `contracts/` — the surface other modules use (move stock + react to events).
- `events.py` — `inventory.StockReceived/StockIssued/StockTransferred`.
- `api/` — DRF endpoints under `/api/inventory/`.

## Costing — weighted average (exact)
Quantities are `Decimal`; value is integer **minor units**. The average unit cost is always
value / quantity (never stored rounded). On issue, cost is taken **proportionally** from the
remaining value (`issue_value = round(value * issue_qty / qty)`), so the running value stays exact and
issuing the whole quantity removes the whole value.

## GL postings
- receipt → Dr Inventory (1200) / Cr Goods-Received-Not-Invoiced (2150)
- issue   → Dr COGS (5000) / Cr Inventory (1200)
- transfer → no GL (value stays within Inventory)

## Invariants (proven by `tests/`)
1. Receipt/issue/transfer update the weighted-average balance correctly.
2. Issuing more than on-hand is rejected (`INV-001`); nothing is written.
3. Each receipt/issue posts a **balanced** journal; the **Inventory GL account balance always equals
   total stock value** (cross-module reconciliation).
4. Each operation is atomic (balance + movement + GL commit together).

## Next slices
UoM conversions, batch/serial/expiry (FEFO), stock counts + variance, reorder alerts, and the
purchasing/sales links (GRNI cleared by a vendor bill; issues driven by deliveries).
