# Session 03 — Costing module (close the accounting loop)

**Goal:** inventory valuation + COGS so the P&L is real, not just revenue. Egyptian SMBs live and die
on margin per item. Recall `conductor-brand` + `erp-frontend`. Branch `feat/module-costing`.

## Scope (v1 — deliberately narrow)
- **Costing methods:** Weighted Average (default) + FIFO. Pick WAVG as the calm default; FIFO as an
  org setting. (Skip LIFO — not IFRS/Egyptian-standard friendly.)
- **Landed cost:** allocate freight/customs/insurance onto received stock (by value or by quantity).
- **COGS posting:** every stock issue (sale delivery) posts COGS = qty × current cost to the GL.
- **Cost layers / valuation:** on-hand value per item per warehouse, always reconcilable to GL
  inventory account.

## Tasks
1. New app `erp/costing/` following the existing module shape (domain/models, repositories, services,
   api). Reuse `AuditedModel`, integer minor units, repository+atomic pattern.
2. **Cost model:** `ItemCost` (item_sku, warehouse, method, moving_avg_cost_minor, updated_at) +
   `CostLayer` for FIFO (item, warehouse, qty_remaining, unit_cost_minor, received_at).
3. **Hook receipts:** when purchasing posts a stock receipt, update WAVG or push a FIFO layer.
   Landed-cost allocation adjusts the layer/avg before it's consumable.
4. **Hook issues:** when inventory posts an issue for a sale delivery, compute COGS from the method,
   consume layers (FIFO) or use avg (WAVG), and post the GL journal (Dr COGS / Cr Inventory).
5. **Invariant:** sum of on-hand layer value == inventory GL account balance, per warehouse. Add the
   reconciliation test (ties into Session 01's invariant suite).
6. **UI:** Item detail gains a "Cost & valuation" tab (current cost, on-hand value, method, recent
   cost movements). Costing report: margin per item/order. Designed empty/loading states.
7. **Money integrity:** rounding policy for cost per unit documented (banker's or half-up — match
   `lib/money.ts`); no fractional cent drift across a full buy→sell cycle (test it).

## Done bar
- Buy 10 @ 100, buy 10 @ 120, sell 15 → COGS + remaining on-hand value correct for both WAVG and
  FIFO, GL balanced, reconciliation invariant holds.
- `gate:all` GREEN; parity + `tsc -b` + `gate03` GREEN.
- DECISIONS.md "Costing 2026-07": methods chosen + why LIFO rejected.
