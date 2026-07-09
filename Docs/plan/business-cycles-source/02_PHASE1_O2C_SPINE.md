# Phase 1 — Order-to-Cash Spine: Delivery + AR Invoice
# LOW RISK — additive schema + new procedures. Existing Sales Order tables get ADDITIVE columns only.

## What you will do in this phase

1. Add quantity-tracking columns to Sales Order lines (rule C1).
2. Create `delivery` + `delivery_line` and `ar_invoice` + `ar_invoice_line` document tables with document chaining (rule C3).
3. Create the two chain procedures: `sp_create_delivery_from_so`, `sp_create_ar_invoice_from_delivery` (the Conductor equivalent of EBS AutoInvoice, radically simplified).
4. Enforce quantity invariants with triggers (rule C2).
5. Seed `field_mutability` and RBAC entries for both new document types.
6. Extend the workspace UI by cloning the Sales Order workspace skeleton.

Nothing existing is deleted or renamed. Only additions.

> **Oracle porting note (add to the porting notes doc):** this phase is the SME-scale equivalent of
> OM → WSH (deliveries) → AR AutoInvoice. `qty_ordered/delivered/invoiced/cancelled` mirrors
> OE_ORDER_LINES_ALL's ORDERED_QUANTITY / SHIPPED_QUANTITY / INVOICED_QUANTITY / CANCELLED_QUANTITY.
> The chain columns replace RA_INTERFACE_LINES interface tables — we chain directly, no interface staging.

## Step 1 — Quantity columns on Sales Order lines

New migration `db/migrations/NNN_o2c_quantities.sql` (use the next number in your sequence):

```sql
ALTER TABLE sales_order_line
  ADD COLUMN qty_delivered  numeric(18,6) NOT NULL DEFAULT 0,
  ADD COLUMN qty_invoiced   numeric(18,6) NOT NULL DEFAULT 0,
  ADD COLUMN qty_cancelled  numeric(18,6) NOT NULL DEFAULT 0,
  ADD COLUMN line_kind      text NOT NULL DEFAULT 'goods'
      CHECK (line_kind IN ('goods','service'));

-- Rule C2 as a table constraint (cheap checks) ...
ALTER TABLE sales_order_line
  ADD CONSTRAINT chk_c2_delivered_within_ordered
    CHECK (qty_delivered + qty_cancelled <= qty_ordered),
  ADD CONSTRAINT chk_c2_nonnegative
    CHECK (qty_delivered >= 0 AND qty_invoiced >= 0 AND qty_cancelled >= 0);

-- ... and the goods/service asymmetry as a trigger (needs row context):
CREATE OR REPLACE FUNCTION trg_c2_invoiced_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.line_kind = 'goods' AND NEW.qty_invoiced > NEW.qty_delivered THEN
    RAISE EXCEPTION 'C2 violation: qty_invoiced (%) exceeds qty_delivered (%) on goods line %',
      NEW.qty_invoiced, NEW.qty_delivered, NEW.id
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.line_kind = 'service' AND NEW.qty_invoiced > NEW.qty_ordered THEN
    RAISE EXCEPTION 'C2 violation: qty_invoiced (%) exceeds qty_ordered (%) on service line %',
      NEW.qty_invoiced, NEW.qty_ordered, NEW.id
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER sales_order_line_c2_guard
  BEFORE INSERT OR UPDATE OF qty_invoiced, qty_delivered, qty_ordered, qty_cancelled
  ON sales_order_line
  FOR EACH ROW EXECUTE FUNCTION trg_c2_invoiced_guard();

-- Rule C1: open quantities are computed, never stored.
CREATE OR REPLACE VIEW v_sales_order_line_open AS
SELECT
  sol.*,
  (sol.qty_ordered - sol.qty_delivered - sol.qty_cancelled) AS qty_open_to_deliver,
  (CASE WHEN sol.line_kind = 'goods'
        THEN sol.qty_delivered - sol.qty_invoiced
        ELSE sol.qty_ordered  - sol.qty_invoiced END)       AS qty_open_to_invoice
FROM sales_order_line sol;
```

## Step 2 — Delivery and AR Invoice document tables

Same migration. Follow the EXACT column conventions of the existing `sales_order` header
(tenant id, document number sequence, state, money typing, audit columns). Shown here with
the canonical names — adapt only if the existing slice uses different audit column names,
and say so in your response.

```sql
CREATE TABLE delivery (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenant(id),
  doc_no           text NOT NULL,
  state            text NOT NULL DEFAULT 'draft'
                   CHECK (state IN ('draft','confirmed','posted','cancelled')),
  -- Rule C3: chaining is data
  source_doc_type  text NOT NULL DEFAULT 'sales_order' CHECK (source_doc_type = 'sales_order'),
  source_doc_id    uuid NOT NULL REFERENCES sales_order(id),
  customer_id      uuid NOT NULL REFERENCES customer(id),
  delivery_date    date NOT NULL,
  warehouse_id     uuid REFERENCES warehouse(id),
  created_by       uuid NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  posted_by        uuid,
  posted_at        timestamptz,
  UNIQUE (tenant_id, doc_no)
);

CREATE TABLE delivery_line (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id      uuid NOT NULL REFERENCES delivery(id) ON DELETE CASCADE,
  source_line_id   uuid NOT NULL REFERENCES sales_order_line(id),
  item_id          uuid NOT NULL REFERENCES item(id),
  qty              numeric(18,6) NOT NULL CHECK (qty > 0),
  uom_id           uuid NOT NULL REFERENCES uom(id)
);

CREATE TABLE ar_invoice (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenant(id),
  doc_no           text NOT NULL,
  state            text NOT NULL DEFAULT 'draft'
                   CHECK (state IN ('draft','posted','cancelled')),   -- ETA states added in Phase 3
  source_doc_type  text NOT NULL CHECK (source_doc_type IN ('delivery','sales_order')),
  source_doc_id    uuid NOT NULL,
  customer_id      uuid NOT NULL REFERENCES customer(id),
  invoice_date     date NOT NULL,
  currency_code    char(3) NOT NULL,
  fx_rate          numeric(18,8),          -- frozen by the SAME mechanism as sales_order at posting
  total_net        numeric(18,4) NOT NULL DEFAULT 0,
  total_tax        numeric(18,4) NOT NULL DEFAULT 0,
  total_gross      numeric(18,4) NOT NULL DEFAULT 0,
  amount_settled   numeric(18,4) NOT NULL DEFAULT 0,   -- maintained by Phase 2 receipt application
  created_by       uuid NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  posted_by        uuid,
  posted_at        timestamptz,
  UNIQUE (tenant_id, doc_no)
);

CREATE TABLE ar_invoice_line (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id       uuid NOT NULL REFERENCES ar_invoice(id) ON DELETE CASCADE,
  source_line_id   uuid REFERENCES sales_order_line(id),
  item_id          uuid NOT NULL REFERENCES item(id),
  qty              numeric(18,6) NOT NULL CHECK (qty > 0),
  uom_id           uuid NOT NULL REFERENCES uom(id),
  unit_price       numeric(18,6) NOT NULL,
  tax_code_id      uuid REFERENCES tax_code(id),
  line_net         numeric(18,4) NOT NULL,
  line_tax         numeric(18,4) NOT NULL,
  line_gross       numeric(18,4) NOT NULL
);

-- Enroll ALL four tables in the universal event log using the existing generic trigger function.
-- (Replace attach_event_log_trigger with the actual mechanism you found in Phase 0, Q3.)
SELECT attach_event_log_trigger('delivery');
SELECT attach_event_log_trigger('delivery_line');
SELECT attach_event_log_trigger('ar_invoice');
SELECT attach_event_log_trigger('ar_invoice_line');
```

## Step 3 — Chain procedures

These are the ONLY way a delivery or AR invoice comes into existence from a source document.
They run INSIDE the guarded write path (call them from it, following the pattern the existing
posting procedure uses). Both are idempotent per source line via the quantity invariants.

```sql
-- Creates a draft delivery for the open-to-deliver quantities of a confirmed sales order.
CREATE OR REPLACE FUNCTION sp_create_delivery_from_so(
  p_tenant_id uuid, p_so_id uuid, p_actor uuid,
  p_lines jsonb  -- [{"source_line_id": "...", "qty": 5}, ...]; NULL = all open quantities
) RETURNS uuid AS $$
DECLARE
  v_so sales_order%ROWTYPE;
  v_delivery_id uuid;
  v_line record;
  v_open numeric;
BEGIN
  SELECT * INTO v_so FROM sales_order
   WHERE id = p_so_id AND tenant_id = p_tenant_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'sales order % not found', p_so_id; END IF;
  IF v_so.state <> 'confirmed' THEN
    RAISE EXCEPTION 'C3: delivery can only be created from a CONFIRMED sales order (state=%)', v_so.state;
  END IF;

  INSERT INTO delivery (tenant_id, doc_no, source_doc_id, customer_id, delivery_date, created_by)
  VALUES (p_tenant_id, next_doc_no(p_tenant_id, 'delivery'), p_so_id, v_so.customer_id, current_date, p_actor)
  RETURNING id INTO v_delivery_id;

  FOR v_line IN
    SELECT sol.id AS source_line_id, sol.item_id, sol.uom_id,
           (sol.qty_ordered - sol.qty_delivered - sol.qty_cancelled) AS qty_open,
           COALESCE((SELECT (x->>'qty')::numeric FROM jsonb_array_elements(p_lines) x
                      WHERE (x->>'source_line_id')::uuid = sol.id),
                    sol.qty_ordered - sol.qty_delivered - sol.qty_cancelled) AS qty_req
      FROM sales_order_line sol
     WHERE sol.sales_order_id = p_so_id AND sol.line_kind = 'goods'
       FOR UPDATE
  LOOP
    IF v_line.qty_req <= 0 THEN CONTINUE; END IF;
    IF v_line.qty_req > v_line.qty_open THEN
      RAISE EXCEPTION 'C2: requested qty % exceeds open-to-deliver % on line %',
        v_line.qty_req, v_line.qty_open, v_line.source_line_id;
    END IF;
    INSERT INTO delivery_line (delivery_id, source_line_id, item_id, qty, uom_id)
    VALUES (v_delivery_id, v_line.source_line_id, v_line.item_id, v_line.qty_req, v_line.uom_id);
  END LOOP;

  IF NOT EXISTS (SELECT 1 FROM delivery_line WHERE delivery_id = v_delivery_id) THEN
    RAISE EXCEPTION 'C3: nothing open to deliver on sales order %', p_so_id;
  END IF;
  RETURN v_delivery_id;
END; $$ LANGUAGE plpgsql;

-- Posting a delivery is what increments qty_delivered on the source lines (never the UI).
CREATE OR REPLACE FUNCTION sp_post_delivery(
  p_tenant_id uuid, p_delivery_id uuid, p_actor uuid
) RETURNS void AS $$
DECLARE v_line record;
BEGIN
  PERFORM 1 FROM delivery
    WHERE id = p_delivery_id AND tenant_id = p_tenant_id AND state = 'confirmed' FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'delivery % must be in CONFIRMED state to post', p_delivery_id;
  END IF;

  FOR v_line IN SELECT dl.source_line_id, dl.qty FROM delivery_line dl
                 WHERE dl.delivery_id = p_delivery_id
  LOOP
    UPDATE sales_order_line
       SET qty_delivered = qty_delivered + v_line.qty
     WHERE id = v_line.source_line_id;          -- C2 trigger + constraint guard this
  END LOOP;

  UPDATE delivery SET state = 'posted', posted_by = p_actor, posted_at = now()
   WHERE id = p_delivery_id;
END; $$ LANGUAGE plpgsql;

-- The simplified AutoInvoice: draft AR invoice from a posted delivery's uninvoiced quantities.
CREATE OR REPLACE FUNCTION sp_create_ar_invoice_from_delivery(
  p_tenant_id uuid, p_delivery_id uuid, p_actor uuid
) RETURNS uuid AS $$
DECLARE
  v_del delivery%ROWTYPE;
  v_invoice_id uuid;
  v_line record;
BEGIN
  SELECT * INTO v_del FROM delivery
   WHERE id = p_delivery_id AND tenant_id = p_tenant_id FOR UPDATE;
  IF NOT FOUND OR v_del.state <> 'posted' THEN
    RAISE EXCEPTION 'C3: AR invoice can only be created from a POSTED delivery';
  END IF;

  INSERT INTO ar_invoice (tenant_id, doc_no, source_doc_type, source_doc_id, customer_id,
                          invoice_date, currency_code, created_by)
  SELECT p_tenant_id, next_doc_no(p_tenant_id, 'ar_invoice'), 'delivery', p_delivery_id,
         v_del.customer_id, current_date, so.currency_code, p_actor
    FROM sales_order so WHERE so.id = v_del.source_doc_id
  RETURNING id INTO v_invoice_id;

  FOR v_line IN
    SELECT dl.source_line_id, dl.item_id, dl.uom_id,
           LEAST(dl.qty, sol.qty_delivered - sol.qty_invoiced) AS qty_to_invoice,
           sol.unit_price, sol.tax_code_id
      FROM delivery_line dl
      JOIN sales_order_line sol ON sol.id = dl.source_line_id
     WHERE dl.delivery_id = p_delivery_id FOR UPDATE OF sol
  LOOP
    IF v_line.qty_to_invoice <= 0 THEN CONTINUE; END IF;
    INSERT INTO ar_invoice_line (invoice_id, source_line_id, item_id, qty, uom_id, unit_price,
                                 tax_code_id, line_net, line_tax, line_gross)
    SELECT v_invoice_id, v_line.source_line_id, v_line.item_id, v_line.qty_to_invoice,
           v_line.uom_id, v_line.unit_price, v_line.tax_code_id,
           t.net, t.tax, t.net + t.tax
      FROM calc_line_tax(v_line.qty_to_invoice, v_line.unit_price, v_line.tax_code_id) t;

    UPDATE sales_order_line
       SET qty_invoiced = qty_invoiced + v_line.qty_to_invoice
     WHERE id = v_line.source_line_id;          -- C2 trigger guards this
  END LOOP;

  UPDATE ar_invoice i SET
    total_net   = (SELECT COALESCE(sum(line_net),0)   FROM ar_invoice_line WHERE invoice_id = i.id),
    total_tax   = (SELECT COALESCE(sum(line_tax),0)   FROM ar_invoice_line WHERE invoice_id = i.id),
    total_gross = (SELECT COALESCE(sum(line_gross),0) FROM ar_invoice_line WHERE invoice_id = i.id)
  WHERE i.id = v_invoice_id;
  RETURN v_invoice_id;
END; $$ LANGUAGE plpgsql;
```

If `next_doc_no` or `calc_line_tax` do not exist in the current slice, create them following the
document-numbering and tax mechanisms already in place (Phase 0 questions 1 and 5 told you where).
Do NOT invent a second numbering or tax mechanism.

## Step 4 — field_mutability + RBAC seeds

Add seed rows for `delivery` and `ar_invoice` following the exact shape found in Phase 0 (Q5):
- `delivery` in `draft`: all header/line fields editable except chain columns (`source_*` NEVER editable in any state — this encodes rule C3 as data).
- `delivery` in `confirmed`: only `delivery_date`, `warehouse_id` editable.
- `delivery` in `posted`/`cancelled`: nothing editable.
- `ar_invoice` in `draft`: quantities/prices editable, chain columns not.
- `ar_invoice` in `posted`: nothing editable (Phase 3 adds ETA transitions, still no field edits).

RBAC: new row-level scopes `delivery:read/write/post`, `ar_invoice:read/write/post`; field-level entries so that `unit_price`, `total_*` are shaped out for roles without pricing visibility — copy the exact pattern used for sales order pricing fields.

## Step 5 — Workspace UI

Clone the Sales Order workspace skeleton for both document types. Requirements (surface from Odoo, remember):
- Delivery form shows at most: customer (read-only from chain), date, warehouse, lines with item/qty. Nothing else visible by default.
- AR Invoice form shows: customer, date, lines, totals, and a chain breadcrumb "SO-nnn → DEL-nnn → INV-nnn" built from the `source_*` columns.
- The document timeline component (existing) must show chain events; no new timeline component.
- Actions exposed as commands in the palette: "Create delivery", "Post delivery", "Create invoice", "Post invoice" — each calls the guarded write path which dispatches to the procedures above.
- Every list/detail endpoint uses the existing RBAC field-shaping interceptor. No new serialization path.

## Verification for Phase 1

```bash
make verify
# New target — add to Makefile in this phase:
# verify-c1-c3: runs db/tests/test_o2c_spine.sql
make verify-cycles
```

Create `db/tests/test_o2c_spine.sql` asserting, at minimum:
1. Delivering more than open qty raises `C2 violation`.
2. Invoicing a goods line beyond delivered qty raises `C2 violation`.
3. `sp_create_delivery_from_so` on a draft SO raises a C3 error.
4. Chain columns are rejected by the write path in every state (mutability check).
5. All four new tables produce event log rows on insert/update.
6. A user without pricing scope receives an AR invoice payload with NO `unit_price`/`total_*` keys (absent, not null).

## What you just built

Sales Order → Delivery → AR Invoice with EBS-grade quantity tracking, chain-as-data, and all
existing guardrails extended to two new document types.

## Next file: 03_PHASE2_O2C_CASH.md
