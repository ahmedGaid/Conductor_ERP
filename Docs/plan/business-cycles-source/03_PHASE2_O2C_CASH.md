# Phase 2 — Order-to-Cash: Customer Receipts & Application
# LOW RISK — new tables + procedures. Only `ar_invoice.amount_settled` is updated on an existing table, and only by the application procedure.

## What you will do in this phase

1. Create `customer_receipt` and `receipt_application` tables.
2. Create `sp_post_receipt` and `sp_apply_receipt` — application is a separate, auditable act (EBS AR pattern: receipt ≠ application).
3. Maintain `ar_invoice.amount_settled` transactionally; invoice settlement state is derived, never stored.
4. Seed mutability + RBAC; extend the invoice workspace with a settlement panel.

> **Oracle porting note:** mirrors AR_CASH_RECEIPTS + AR_RECEIVABLE_APPLICATIONS, collapsed to
> SME scale: no lockboxes, no receipt classes, one receipt method table. Unapplied/on-account
> balance is the receipt amount minus its applications — computed, per rule C1's spirit.

## Step 1 — Tables

Migration `db/migrations/NNN_o2c_cash.sql`:

```sql
CREATE TABLE customer_receipt (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL REFERENCES tenant(id),
  doc_no         text NOT NULL,
  state          text NOT NULL DEFAULT 'draft'
                 CHECK (state IN ('draft','posted','cancelled')),
  customer_id    uuid NOT NULL REFERENCES customer(id),
  receipt_date   date NOT NULL,
  currency_code  char(3) NOT NULL,
  fx_rate        numeric(18,8),
  amount         numeric(18,4) NOT NULL CHECK (amount > 0),
  method_id      uuid NOT NULL REFERENCES receipt_method(id),
  reference      text,
  created_by     uuid NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  posted_by      uuid,
  posted_at      timestamptz,
  UNIQUE (tenant_id, doc_no)
);

CREATE TABLE receipt_method (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid NOT NULL REFERENCES tenant(id),
  name       text NOT NULL,
  kind       text NOT NULL CHECK (kind IN ('cash','bank_transfer','cheque','card','wallet')),
  account_id uuid,           -- GL account, wired fully in Phase 5
  UNIQUE (tenant_id, name)
);

CREATE TABLE receipt_application (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    uuid NOT NULL REFERENCES tenant(id),
  receipt_id   uuid NOT NULL REFERENCES customer_receipt(id),
  invoice_id   uuid NOT NULL REFERENCES ar_invoice(id),
  amount       numeric(18,4) NOT NULL CHECK (amount > 0),
  applied_by   uuid NOT NULL,
  applied_at   timestamptz NOT NULL DEFAULT now(),
  reversed_at  timestamptz,          -- rule C8: unapply = reversal row, never delete
  reversed_by  uuid
);

SELECT attach_event_log_trigger('customer_receipt');
SELECT attach_event_log_trigger('receipt_application');

-- Derived settlement view — the ONLY source of "paid / partially_paid / unpaid".
CREATE OR REPLACE VIEW v_ar_invoice_settlement AS
SELECT i.id AS invoice_id, i.total_gross, i.amount_settled,
       (i.total_gross - i.amount_settled) AS amount_open,
       CASE WHEN i.amount_settled = 0 THEN 'unpaid'
            WHEN i.amount_settled < i.total_gross THEN 'partially_paid'
            ELSE 'paid' END AS settlement_state
FROM ar_invoice i WHERE i.state = 'posted';
```

Note table creation order: create `receipt_method` BEFORE `customer_receipt` in the actual
migration (the FK requires it); shown out of order above for readability only.

## Step 2 — Procedures

```sql
CREATE OR REPLACE FUNCTION sp_apply_receipt(
  p_tenant_id uuid, p_receipt_id uuid, p_invoice_id uuid,
  p_amount numeric, p_actor uuid
) RETURNS uuid AS $$
DECLARE
  v_receipt customer_receipt%ROWTYPE;
  v_invoice ar_invoice%ROWTYPE;
  v_unapplied numeric;
  v_app_id uuid;
BEGIN
  SELECT * INTO v_receipt FROM customer_receipt
   WHERE id = p_receipt_id AND tenant_id = p_tenant_id FOR UPDATE;
  SELECT * INTO v_invoice FROM ar_invoice
   WHERE id = p_invoice_id AND tenant_id = p_tenant_id FOR UPDATE;

  IF v_receipt.state <> 'posted' THEN
    RAISE EXCEPTION 'receipt must be posted before application';
  END IF;
  IF v_invoice.state <> 'posted' THEN
    RAISE EXCEPTION 'cannot apply to a non-posted invoice';
  END IF;
  IF v_receipt.customer_id <> v_invoice.customer_id THEN
    RAISE EXCEPTION 'receipt and invoice belong to different customers';
  END IF;
  IF v_receipt.currency_code <> v_invoice.currency_code THEN
    RAISE EXCEPTION 'cross-currency application not supported in this phase';
  END IF;

  SELECT v_receipt.amount - COALESCE(sum(a.amount),0) INTO v_unapplied
    FROM receipt_application a
   WHERE a.receipt_id = p_receipt_id AND a.reversed_at IS NULL;

  IF p_amount > v_unapplied THEN
    RAISE EXCEPTION 'application % exceeds unapplied balance %', p_amount, v_unapplied;
  END IF;
  IF p_amount > (v_invoice.total_gross - v_invoice.amount_settled) THEN
    RAISE EXCEPTION 'application % exceeds invoice open amount %',
      p_amount, v_invoice.total_gross - v_invoice.amount_settled;
  END IF;

  INSERT INTO receipt_application (tenant_id, receipt_id, invoice_id, amount, applied_by)
  VALUES (p_tenant_id, p_receipt_id, p_invoice_id, p_amount, p_actor)
  RETURNING id INTO v_app_id;

  UPDATE ar_invoice SET amount_settled = amount_settled + p_amount WHERE id = p_invoice_id;
  RETURN v_app_id;
END; $$ LANGUAGE plpgsql;

-- Rule C8: unapplication is a reversal, not a delete.
CREATE OR REPLACE FUNCTION sp_unapply_receipt(
  p_tenant_id uuid, p_application_id uuid, p_actor uuid
) RETURNS void AS $$
DECLARE v_app receipt_application%ROWTYPE;
BEGIN
  SELECT * INTO v_app FROM receipt_application
   WHERE id = p_application_id AND tenant_id = p_tenant_id AND reversed_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'application not found or already reversed'; END IF;

  UPDATE receipt_application SET reversed_at = now(), reversed_by = p_actor
   WHERE id = p_application_id;
  UPDATE ar_invoice SET amount_settled = amount_settled - v_app.amount
   WHERE id = v_app.invoice_id;
END; $$ LANGUAGE plpgsql;
```

`sp_post_receipt` follows the exact posting pattern of `sp_post_delivery` (state guard → freeze FX
using the existing mechanism → set posted state). Write it in that pattern; in Phase 5 it gains a
period guard and journal event emission.

## Step 3 — Mutability, RBAC, UI

- Mutability: `customer_receipt` draft = all editable except nothing chained; posted = nothing.
- Applications are NOT edited — created and reversed only. Encode by giving `receipt_application` no editable fields in any state.
- RBAC scopes: `receipt:read/write/post/apply`. Applying money is a distinct permission from recording money — keep them separate scopes.
- UI: settlement panel inside the AR Invoice workspace: open amount, applications list (with reversed ones struck through — the event log is visible history, per the timeline pattern), and an "Apply receipt" command showing only this customer's posted receipts with unapplied balance.

## Verification for Phase 2

Extend `verify-cycles`; create `db/tests/test_o2c_cash.sql` asserting:
1. Over-application beyond unapplied balance raises.
2. Over-application beyond invoice open amount raises.
3. Cross-customer application raises.
4. Unapply restores `amount_settled` and leaves the reversal row (count of rows unchanged).
5. Settlement state transitions unpaid → partially_paid → paid purely via the view.

```bash
make verify && make verify-cycles
```

## What you just built

Order-to-Cash is now a complete cycle: order → delivery → invoice → cash, with application as a
first-class auditable act.

## Next file: 04_PHASE3_ETA_LIFECYCLE.md
