# Phase 4 — Procure-to-Pay with 3-Way Match
# MEDIUM RISK — largest phase. Entirely new document family; mirrors Phase 1–2 patterns on the purchasing side. Split your work into the sub-steps below and verify after EACH.

## What you will do in this phase

1. `purchase_order` + lines (with C1 quantity columns: `qty_ordered/received/invoiced/cancelled`).
2. `goods_receipt` + lines, chained from PO (mirror of Phase 1 delivery, direction reversed).
3. `supplier_invoice` + lines, with **3-way match** (rule C5) and tolerance table.
4. `supplier_payment` + `payment_application` (mirror of Phase 2 receipts).
5. Mutability, RBAC, workspaces for all four document types.

> **Oracle porting note:** this is PO → RCV → AP invoice matching, SME-scale. The tolerance table
> replaces AP tolerance templates/options. Match status on the supplier invoice replaces the
> holds framework: instead of EBS's dozens of hold types, Conductor has one `match_status` with a
> stored list of match exceptions — visible, human-readable, resolved by explicit action.

## Step 1 — Purchase Order (mirror sales_order conventions exactly)

Migration `db/migrations/NNN_p2p.sql`. Reuse every convention from Phase 1; differences only:

```sql
CREATE TABLE purchase_order (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL REFERENCES tenant(id),
  doc_no         text NOT NULL,
  state          text NOT NULL DEFAULT 'draft'
                 CHECK (state IN ('draft','confirmed','closed','cancelled')),
  supplier_id    uuid NOT NULL REFERENCES supplier(id),
  order_date     date NOT NULL,
  currency_code  char(3) NOT NULL,
  fx_rate        numeric(18,8),
  created_by     uuid NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  confirmed_by   uuid, confirmed_at timestamptz,
  UNIQUE (tenant_id, doc_no)
);

CREATE TABLE purchase_order_line (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  po_id          uuid NOT NULL REFERENCES purchase_order(id) ON DELETE CASCADE,
  item_id        uuid NOT NULL REFERENCES item(id),
  line_kind      text NOT NULL DEFAULT 'goods' CHECK (line_kind IN ('goods','service')),
  qty_ordered    numeric(18,6) NOT NULL CHECK (qty_ordered > 0),
  qty_received   numeric(18,6) NOT NULL DEFAULT 0,
  qty_invoiced   numeric(18,6) NOT NULL DEFAULT 0,
  qty_cancelled  numeric(18,6) NOT NULL DEFAULT 0,
  uom_id         uuid NOT NULL REFERENCES uom(id),
  unit_price     numeric(18,6) NOT NULL,
  tax_code_id    uuid REFERENCES tax_code(id),
  CONSTRAINT chk_c2_received CHECK (qty_received + qty_cancelled <= qty_ordered),
  CONSTRAINT chk_c2_nonneg  CHECK (qty_received >= 0 AND qty_invoiced >= 0 AND qty_cancelled >= 0)
);
```

Add the goods/service invoiced-guard trigger exactly like Phase 1 (`qty_invoiced <= qty_received`
for goods, `<= qty_ordered` for services) and the open-quantity view
`v_purchase_order_line_open`. Attach event log triggers to every new table in this phase.

## Step 2 — Goods Receipt

Tables `goods_receipt` / `goods_receipt_line` mirroring Phase 1's delivery pair
(`source_doc_type = 'purchase_order'`, `source_line_id → purchase_order_line`). Procedures
`sp_create_receipt_from_po` and `sp_post_goods_receipt` are direct structural mirrors of
`sp_create_delivery_from_so` / `sp_post_delivery` — same locking, same C2/C3 error style, with
`qty_received` incremented at posting. Write them fully; do not reference Phase 1 code at runtime.

## Step 3 — Supplier Invoice + 3-way match (the heart of this phase)

```sql
CREATE TABLE match_tolerance (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          uuid NOT NULL REFERENCES tenant(id),
  name               text NOT NULL,
  price_tolerance_pct numeric(7,4) NOT NULL DEFAULT 0,     -- e.g. 2.0 = ±2%
  qty_tolerance_pct   numeric(7,4) NOT NULL DEFAULT 0,
  amount_tolerance    numeric(18,4) NOT NULL DEFAULT 0,    -- absolute cap per line
  is_default         boolean NOT NULL DEFAULT false,
  UNIQUE (tenant_id, name)
);

CREATE TABLE supplier_invoice (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL REFERENCES tenant(id),
  doc_no         text NOT NULL,
  supplier_ref   text,                          -- the supplier's own invoice number
  state          text NOT NULL DEFAULT 'draft'
                 CHECK (state IN ('draft','matched','posted','cancelled')),
  match_status   text NOT NULL DEFAULT 'unmatched'
                 CHECK (match_status IN ('unmatched','matched','exception')),
  supplier_id    uuid NOT NULL REFERENCES supplier(id),
  invoice_date   date NOT NULL,
  currency_code  char(3) NOT NULL,
  fx_rate        numeric(18,8),
  total_net      numeric(18,4) NOT NULL DEFAULT 0,
  total_tax      numeric(18,4) NOT NULL DEFAULT 0,
  total_gross    numeric(18,4) NOT NULL DEFAULT 0,
  amount_settled numeric(18,4) NOT NULL DEFAULT 0,
  created_by     uuid NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  posted_by      uuid, posted_at timestamptz,
  UNIQUE (tenant_id, doc_no),
  UNIQUE (tenant_id, supplier_id, supplier_ref)   -- duplicate supplier invoice guard
);

CREATE TABLE supplier_invoice_line (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id     uuid NOT NULL REFERENCES supplier_invoice(id) ON DELETE CASCADE,
  source_line_id uuid NOT NULL REFERENCES purchase_order_line(id),   -- C3: always PO-backed
  item_id        uuid NOT NULL REFERENCES item(id),
  qty            numeric(18,6) NOT NULL CHECK (qty > 0),
  uom_id         uuid NOT NULL REFERENCES uom(id),
  unit_price     numeric(18,6) NOT NULL,
  tax_code_id    uuid REFERENCES tax_code(id),
  line_net       numeric(18,4) NOT NULL,
  line_tax       numeric(18,4) NOT NULL,
  line_gross     numeric(18,4) NOT NULL
);

CREATE TABLE match_exception (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id     uuid NOT NULL REFERENCES supplier_invoice(id) ON DELETE CASCADE,
  line_id        uuid REFERENCES supplier_invoice_line(id),
  kind           text NOT NULL CHECK (kind IN ('qty_over_received','price_variance','amount_variance')),
  detail         jsonb NOT NULL,       -- {"invoiced": ..., "received": ..., "tolerance_pct": ...}
  raised_at      timestamptz NOT NULL DEFAULT now(),
  resolved_at    timestamptz,
  resolved_by    uuid,
  resolution     text CHECK (resolution IN ('tolerance_updated','po_amended','invoice_corrected','accepted_by_approver'))
);
```

The match function (rule C5 — tolerances are data):

```sql
CREATE OR REPLACE FUNCTION sp_match_supplier_invoice(
  p_tenant_id uuid, p_invoice_id uuid, p_actor uuid
) RETURNS text AS $$   -- returns resulting match_status
DECLARE
  v_inv supplier_invoice%ROWTYPE;
  v_tol match_tolerance%ROWTYPE;
  v_line record;
  v_exceptions int := 0;
  v_open_to_invoice numeric;
  v_price_var_pct numeric;
BEGIN
  SELECT * INTO v_inv FROM supplier_invoice
   WHERE id = p_invoice_id AND tenant_id = p_tenant_id FOR UPDATE;
  IF v_inv.state <> 'draft' THEN
    RAISE EXCEPTION 'C5: match runs on draft invoices only (state=%)', v_inv.state;
  END IF;

  SELECT * INTO v_tol FROM match_tolerance
   WHERE tenant_id = p_tenant_id AND is_default LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'C5: no default match_tolerance configured for tenant';
  END IF;

  -- clear unresolved exceptions from previous match runs (resolved ones stay: rule C8)
  DELETE FROM match_exception
   WHERE invoice_id = p_invoice_id AND resolved_at IS NULL;

  FOR v_line IN
    SELECT sil.id, sil.qty, sil.unit_price, pol.unit_price AS po_price, pol.line_kind,
           (CASE WHEN pol.line_kind = 'goods'
                 THEN pol.qty_received - pol.qty_invoiced
                 ELSE pol.qty_ordered  - pol.qty_invoiced END) AS open_to_invoice
      FROM supplier_invoice_line sil
      JOIN purchase_order_line pol ON pol.id = sil.source_line_id
     WHERE sil.invoice_id = p_invoice_id
       FOR UPDATE OF pol
  LOOP
    -- Quantity leg (3-way: invoice vs receipt)
    IF v_line.qty > v_line.open_to_invoice * (1 + v_tol.qty_tolerance_pct / 100.0) THEN
      INSERT INTO match_exception (invoice_id, line_id, kind, detail)
      VALUES (p_invoice_id, v_line.id, 'qty_over_received',
              jsonb_build_object('invoiced', v_line.qty, 'open', v_line.open_to_invoice,
                                 'tolerance_pct', v_tol.qty_tolerance_pct));
      v_exceptions := v_exceptions + 1;
    END IF;

    -- Price leg (invoice vs PO)
    IF v_line.po_price > 0 THEN
      v_price_var_pct := abs(v_line.unit_price - v_line.po_price) / v_line.po_price * 100.0;
      IF v_price_var_pct > v_tol.price_tolerance_pct
         AND abs((v_line.unit_price - v_line.po_price) * v_line.qty) > v_tol.amount_tolerance THEN
        INSERT INTO match_exception (invoice_id, line_id, kind, detail)
        VALUES (p_invoice_id, v_line.id, 'price_variance',
                jsonb_build_object('invoice_price', v_line.unit_price, 'po_price', v_line.po_price,
                                   'variance_pct', round(v_price_var_pct, 4),
                                   'tolerance_pct', v_tol.price_tolerance_pct));
        v_exceptions := v_exceptions + 1;
      END IF;
    END IF;
  END LOOP;

  UPDATE supplier_invoice
     SET match_status = CASE WHEN v_exceptions = 0 THEN 'matched' ELSE 'exception' END,
         state        = CASE WHEN v_exceptions = 0 THEN 'matched' ELSE state END
   WHERE id = p_invoice_id;

  RETURN CASE WHEN v_exceptions = 0 THEN 'matched' ELSE 'exception' END;
END; $$ LANGUAGE plpgsql;
```

Posting rule: `sp_post_supplier_invoice` requires `state = 'matched'`; at posting it increments
`qty_invoiced` on the PO lines (C2 trigger guards) and freezes FX. Exception resolution
`sp_resolve_match_exception` records `resolved_by` + `resolution`, requires the dedicated RBAC
scope `supplier_invoice:resolve_exception`, and forces a fresh `sp_match_supplier_invoice` run —
resolution never sets `matched` directly.

## Step 4 — Supplier Payment

Structural mirror of Phase 2: `supplier_payment`, `payment_method` (or reuse `receipt_method`
generalized — check what fits the existing naming; prefer one `settlement_method` table if the
migration is clean and additive), `payment_application` with the same reversal-only unapply, same
over-application guards, `amount_settled` maintained on `supplier_invoice`, derived
`v_supplier_invoice_settlement` view.

## Step 5 — Mutability, RBAC, UI

- Mutability seeds for all four document types following Phase 1/2 patterns; `match_status`, `supplier_ref` uniqueness, and all chain/ETA-style system columns never editable.
- RBAC: purchasing scopes are distinct from sales scopes; `resolve_exception` and `apply` are their own scopes (segregation of duties — the person recording invoices should not silently approve variances).
- UI: PO/receipt/invoice/payment workspaces cloned from the sales side. The supplier invoice workspace centers the match panel: per-line invoiced vs received vs ordered, exceptions as human-readable cards with a resolve action. Odoo-surface rule: default view shows only exceptions, not every matched line.

## Verification for Phase 4

`db/tests/test_p2p.sql` asserting at minimum:
1. Invoice qty over received (beyond tolerance) yields `exception` + a `qty_over_received` row.
2. Price variance beyond both pct and amount tolerance yields `price_variance`; within either tolerance yields none.
3. Posting an unmatched invoice raises.
4. Duplicate `(supplier_id, supplier_ref)` raises.
5. Exception resolution requires the scope and re-runs matching.
6. Payment over-application raises; unapply is reversal-only.
7. All new tables emit event log rows.

```bash
make verify && make verify-cycles
```

## What you just built

The full purchasing cycle with the single feature that separates an ERP from an invoicing app:
receipt-backed, tolerance-controlled 3-way match.

## Next file: 06_PHASE5_R2R.md
