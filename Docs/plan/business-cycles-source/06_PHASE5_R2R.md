# Phase 5 — Record-to-Report Foundation: Journal Events, Periods, Close Guard
# MEDIUM RISK — this phase touches every posting procedure built so far. It is deliberately LAST so all posting points already exist and can be wired in one sweep.

## What you will do in this phase

1. Create `accounting_period` with a per-module-free, single close state (SME simplification of EBS's per-application period statuses).
2. Create `journal_event` — balanced debit/credit rows emitted by every posting (rule C7).
3. Create the period guard `fn_assert_open_period` and wire it into EVERY posting procedure (rule C6).
4. Create `account` (chart of accounts, minimal) and `posting_rule` — which accounts each document type hits, as data.
5. Trial balance view. No financial statements UI in this phase — the view is the deliverable.

> **Oracle porting note:** journal_event ≈ XLA journal lines collapsed with GL_JE_LINES — no
> subledger/GL separation at SME scale; one event table IS the ledger. posting_rule ≈ a radically
> simplified SLA: account derivation as a lookup table, not a rules engine. accounting_period ≈
> GL_PERIOD_STATUSES with exactly two states.

## Step 1 — Periods and accounts

Migration `db/migrations/NNN_r2r_foundation.sql`:

```sql
CREATE TABLE accounting_period (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenant(id),
  period_name text NOT NULL,                      -- '2026-07'
  start_date  date NOT NULL,
  end_date    date NOT NULL,
  state       text NOT NULL DEFAULT 'open' CHECK (state IN ('open','closed')),
  closed_by   uuid, closed_at timestamptz,
  UNIQUE (tenant_id, period_name),
  CHECK (start_date <= end_date)
);

-- No overlapping periods per tenant.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE accounting_period
  ADD CONSTRAINT no_overlap EXCLUDE USING gist
    (tenant_id WITH =, daterange(start_date, end_date, '[]') WITH &&);

CREATE TABLE account (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid NOT NULL REFERENCES tenant(id),
  code       text NOT NULL,
  name       text NOT NULL,
  name_ar    text,
  kind       text NOT NULL CHECK (kind IN ('asset','liability','equity','revenue','expense')),
  is_active  boolean NOT NULL DEFAULT true,
  UNIQUE (tenant_id, code)
);

CREATE TABLE posting_rule (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL REFERENCES tenant(id),
  doc_type      text NOT NULL,        -- 'ar_invoice','customer_receipt','supplier_invoice','supplier_payment','goods_receipt'
  leg           text NOT NULL,        -- 'receivable','revenue','tax_output','cash','payable','expense','tax_input','grni'
  account_id    uuid NOT NULL REFERENCES account(id),
  UNIQUE (tenant_id, doc_type, leg)
);
```

## Step 2 — Journal events (rule C7)

```sql
CREATE TABLE journal_event (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL REFERENCES tenant(id),
  event_group   uuid NOT NULL,        -- one posting = one group; group must balance
  doc_type      text NOT NULL,
  doc_id        uuid NOT NULL,
  account_id    uuid NOT NULL REFERENCES account(id),
  period_id     uuid NOT NULL REFERENCES accounting_period(id),
  event_date    date NOT NULL,
  currency_code char(3) NOT NULL,
  fx_rate       numeric(18,8) NOT NULL DEFAULT 1,
  debit         numeric(18,4) NOT NULL DEFAULT 0 CHECK (debit >= 0),
  credit        numeric(18,4) NOT NULL DEFAULT 0 CHECK (credit >= 0),
  created_at    timestamptz NOT NULL DEFAULT now(),
  created_by    uuid NOT NULL,
  CHECK (debit = 0 OR credit = 0),
  CHECK (debit <> 0 OR credit <> 0)
);

SELECT attach_event_log_trigger('journal_event');

-- Journal events are append-only (rule C8): reversals are new rows with a new event_group.
CREATE OR REPLACE FUNCTION trg_journal_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C8: journal_event rows are append-only';
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER journal_event_immutable
  BEFORE UPDATE OR DELETE ON journal_event
  FOR EACH ROW EXECUTE FUNCTION trg_journal_immutable();

-- Balance enforcement per group: deferred constraint trigger at transaction end.
CREATE OR REPLACE FUNCTION trg_journal_group_balanced() RETURNS trigger AS $$
DECLARE v_diff numeric;
BEGIN
  SELECT COALESCE(sum(debit) - sum(credit), 0) INTO v_diff
    FROM journal_event WHERE event_group = NEW.event_group;
  IF v_diff <> 0 THEN
    RAISE EXCEPTION 'C7: journal group % does not balance (diff=%)', NEW.event_group, v_diff;
  END IF;
  RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER journal_group_balanced
  AFTER INSERT ON journal_event
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_journal_group_balanced();
```

## Step 3 — Period guard (rule C6) and posting-procedure wiring

```sql
CREATE OR REPLACE FUNCTION fn_assert_open_period(
  p_tenant_id uuid, p_date date
) RETURNS uuid AS $$   -- returns period_id for journal rows
DECLARE v_period accounting_period%ROWTYPE;
BEGIN
  SELECT * INTO v_period FROM accounting_period
   WHERE tenant_id = p_tenant_id AND p_date BETWEEN start_date AND end_date;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'C6: no accounting period defined for %', p_date;
  END IF;
  IF v_period.state = 'closed' THEN
    RAISE EXCEPTION 'C6: period % is closed', v_period.period_name;
  END IF;
  RETURN v_period.id;
END; $$ LANGUAGE plpgsql;
```

Now modify each posting procedure from Phases 1–4 (`sp_post_delivery` only if you decided goods
movements post to GRNI — for SME v1, deliveries do NOT emit journal events; document that choice)
so that, INSIDE the same transaction:

1. First line: `v_period_id := fn_assert_open_period(p_tenant_id, <document date>);`
2. After the state change: emit journal rows via a helper `fn_emit_journal(...)` that reads
   `posting_rule` for the doc type and writes one balanced `event_group`:
   - `ar_invoice` post: DR receivable `total_gross` / CR revenue `total_net` / CR tax_output `total_tax`
   - `customer_receipt` post: DR cash / CR receivable
   - `supplier_invoice` post: DR expense `total_net` + DR tax_input `total_tax` / CR payable `total_gross`
   - `supplier_payment` post: DR payable / CR cash
3. If a required `posting_rule` leg is missing, RAISE — never post silently without accounting.

Write `fn_emit_journal` fully (loop over legs, look up accounts, insert rows with the frozen
`fx_rate` from the document, single `event_group := gen_random_uuid()`).

This is the ONLY phase allowed to modify existing procedures. Modify by inserting the two calls;
do not restructure procedure bodies. Diff must show additions only inside each procedure.

## Step 4 — Period close

```sql
CREATE OR REPLACE FUNCTION sp_close_period(
  p_tenant_id uuid, p_period_id uuid, p_actor uuid
) RETURNS void AS $$
DECLARE v_period accounting_period%ROWTYPE; v_drafts int;
BEGIN
  SELECT * INTO v_period FROM accounting_period
   WHERE id = p_period_id AND tenant_id = p_tenant_id FOR UPDATE;
  IF v_period.state = 'closed' THEN RAISE EXCEPTION 'period already closed'; END IF;

  -- SME close checklist v1: warn-level checks are returned to the UI by the API layer;
  -- the single hard block is: nothing can be posted into it afterwards (that's the guard).
  UPDATE accounting_period SET state = 'closed', closed_by = p_actor, closed_at = now()
   WHERE id = p_period_id;
END; $$ LANGUAGE plpgsql;
```

Reopening a period is a v1 NON-feature: no `sp_reopen_period`. Corrections go into the current
open period as reversal groups (rule C8). State this in the porting notes — it is a deliberate
divergence from EBS.

## Step 5 — Trial balance view + minimal UI

```sql
CREATE OR REPLACE VIEW v_trial_balance AS
SELECT je.tenant_id, ap.period_name, a.code, a.name, a.kind,
       sum(je.debit)  AS total_debit,
       sum(je.credit) AS total_credit,
       sum(je.debit) - sum(je.credit) AS balance
FROM journal_event je
JOIN account a ON a.id = je.account_id
JOIN accounting_period ap ON ap.id = je.period_id
GROUP BY je.tenant_id, ap.period_name, a.code, a.name, a.kind;
```

UI: a single "Accounting" workspace page — period list with close action (scope
`period:close`, its own permission), trial balance table per period, and each journal group
drill-down linking back to its source document (doc_type + doc_id → existing workspace routes).
Seed a minimal Egyptian SME chart of accounts (Arabic + English names) as tenant-template data.

## Verification for Phase 5

`db/tests/test_r2r.sql` asserting:
1. Posting any document dated in a closed period raises C6 — test for ar_invoice, receipt, supplier_invoice, payment.
2. An unbalanced journal group is rejected at commit.
3. journal_event UPDATE and DELETE both raise.
4. Missing posting_rule leg blocks posting with a clear error.
5. Trial balance debits = credits for every period after a scripted O2C + P2P run.
6. Period overlap insertion raises.

Also add the END-TO-END smoke test `db/tests/test_full_cycle.sql`: SO → deliver → invoice → ETA
accept (mock) → receipt → apply; PO → receive → supplier invoice → match → post → pay → apply;
close period; assert trial balance balances and every document rejects edits.

```bash
make verify && make verify-cycles
```

## What you just built

Every business event now lands in a balanced, immutable ledger inside a governed period. Conductor
is now a three-cycle ERP, not a document app.

## Next file: 07_VERIFICATION.md
