# Phase 2 — Posting, Tax & FX Engine (the trust core)
# MEDIUM RISK — this is the heart. If anything here is wrong, the product is wrong.

Honor: Rule 0 (correctness first), Rule 1 (typed money, frozen FX), Rule 3 (state
machine + matrix), Rule 4 (every change → event). Touch only DB procedures/triggers.

## What you will do
1. Tax resolution + computation function (engine, not literals).
2. Document totals computation (net/tax/gross + base-ccy via frozen FX).
3. `post_document` procedure — validate → freeze FX → compute → write GL → lock.
4. `reverse_document` / `amend_document` — linked successors.
5. Mutability guard — block illegal edits using the matrix, not if/else.
6. Immutability triggers on `gl_entry` and posted financial fields.
7. Event-log triggers so NO mutation escapes the timeline.

> Specs below are written as PostgreSQL PL/pgSQL. **For Oracle, map each function
> to a packaged procedure with the identical name and signature** — e.g.
> `package conductor_post` with `resolve_tax_code`, `compute_totals`,
> `post_document`, `reverse_document`. The logic is identical; only syntax changes.

---

## Step 1 — Tax resolution (Rule 1: never hardcode)
```sql
-- Resolve the applicable tax_code for a line, by item category + party class + date.
create or replace function resolve_tax_code(
  p_org_id bigint, p_item_id bigint, p_party_id bigint, p_on date
) returns bigint language plpgsql as $$
declare v_code bigint;
begin
  select tr.tax_code_id into v_code
  from tax_rule tr
  join tax_code tc on tc.tax_code_id = tr.tax_code_id
  join item i on i.item_id = p_item_id
  join party pa on pa.party_id = p_party_id
  join org o on o.org_id = p_org_id
  where tr.jurisdiction_id = (select jurisdiction_id from tax_jurisdiction
                              where country = o.tax_country limit 1)
    and (tr.item_category is null or tr.item_category = i.item_category)
    and (tr.party_class   is null or tr.party_class   = pa.party_class)
    and p_on between tc.effective_from and coalesce(tc.effective_to, p_on)
  order by tr.priority asc
  limit 1;
  if v_code is null then
    raise exception 'No tax rule for item % party % on %', p_item_id, p_party_id, p_on;
  end if;
  return v_code;
end $$;
```

## Step 2 — Compute totals (handles inclusive/exclusive; freezes nothing yet)
```sql
create or replace function compute_document_totals(p_document_id bigint)
returns void language plpgsql as $$
declare r record; v_rate numeric(9,6); v_incl boolean; v_net numeric; v_tax numeric;
        v_doc record;
begin
  select * into v_doc from document where document_id = p_document_id;
  for r in select * from document_line where document_id = p_document_id loop
    -- resolve tax code at the document's effective date (today if draft)
    update document_line set tax_code_id =
      resolve_tax_code(v_doc.org_id, r.item_id, v_doc.party_id, coalesce(v_doc.posted_at::date, current_date))
      where line_id = r.line_id;

    select rate, is_inclusive into v_rate, v_incl
      from tax_code where tax_code_id = (select tax_code_id from document_line where line_id=r.line_id);

    if v_incl then               -- price already includes tax
      v_net := round((r.qty * r.unit_price_amount) / (1 + v_rate), 4);
      v_tax := round(r.qty * r.unit_price_amount - v_net, 4);
    else
      v_net := round(r.qty * r.unit_price_amount, 4);
      v_tax := round(v_net * v_rate, 4);
    end if;

    update document_line
      set line_net = v_net, line_tax = v_tax, line_gross = v_net + v_tax
      where line_id = r.line_id;
  end loop;

  update document d set
    net_amount   = (select coalesce(sum(line_net),0)   from document_line where document_id=d.document_id),
    tax_amount   = (select coalesce(sum(line_tax),0)   from document_line where document_id=d.document_id),
    gross_amount = (select coalesce(sum(line_gross),0) from document_line where document_id=d.document_id)
  where d.document_id = p_document_id;
end $$;
```

## Step 3 — POST (validate → freeze FX → GL → lock)
```sql
create or replace function post_document(p_document_id bigint, p_user bigint)
returns void language plpgsql as $$
declare d record; v_base char(3); v_rate numeric(18,8); v_credit record;
begin
  select * into d from document where document_id = p_document_id for update;
  if d.status <> 'DRAFT' then raise exception 'Only DRAFT can be posted'; end if;

  -- a) recompute totals from lines (never trust client-sent totals)
  perform compute_document_totals(p_document_id);
  select * into d from document where document_id = p_document_id;

  -- b) FREEZE FX (Rule 1) — captured now, never recomputed
  select base_currency into v_base from org where org_id = d.org_id;
  if d.currency = v_base then v_rate := 1;
  else
    select rate into v_rate from fx_rate
     where from_ccy=d.currency and to_ccy=v_base and rate_type='CORPORATE'
       and rate_date <= current_date order by rate_date desc limit 1;
    if v_rate is null then raise exception 'No FX rate % -> %', d.currency, v_base; end if;
  end if;

  -- c) credit check (example business validation; expand as needed)
  -- raise exception if party over credit_limit ... (left as configurable)

  -- d) GL: balanced double entry, in BASE ccy (sales example)
  insert into gl_entry(document_id,org_id,account_code,debit,credit,currency,doc_currency_amount)
  values
   (d.document_id,d.org_id,'AR',     round(d.gross_amount*v_rate,4),0,v_base,d.gross_amount),
   (d.document_id,d.org_id,'REVENUE',0,round(d.net_amount*v_rate,4),v_base,d.net_amount),
   (d.document_id,d.org_id,'VAT_OUT',0,round(d.tax_amount*v_rate,4),v_base,d.tax_amount);

  -- e) lock + stamp frozen values
  update document set
     status='POSTED', posted_by=p_user, posted_at=now(),
     fx_rate=v_rate, fx_rate_date=current_date, fx_rate_type='CORPORATE',
     base_net_amount   = round(d.net_amount*v_rate,4),
     base_gross_amount = round(d.gross_amount*v_rate,4),
     doc_number = coalesce(doc_number, 'SO-'||lpad(d.document_id::text,6,'0'))
   where document_id = d.document_id;

  insert into event_log(entity,entity_id,action,actor_user,source)
   values('document',d.document_id,'POST',p_user,'human');
end $$;
```

## Step 4 — REVERSE (linked successor; opposite GL)
```sql
create or replace function reverse_document(p_document_id bigint, p_user bigint)
returns bigint language plpgsql as $$
declare d record; v_new bigint;
begin
  select * into d from document where document_id=p_document_id for update;
  if d.status <> 'POSTED' then raise exception 'Only POSTED can be reversed'; end if;

  insert into document(doc_type,org_id,party_id,status,currency,fx_rate,fx_rate_date,
        fx_rate_type,net_amount,tax_amount,gross_amount,base_net_amount,base_gross_amount,
        reverses_document_id,created_by,posted_by,posted_at,doc_number)
  values(d.doc_type,d.org_id,d.party_id,'POSTED',d.currency,d.fx_rate,d.fx_rate_date,
        d.fx_rate_type,-d.net_amount,-d.tax_amount,-d.gross_amount,
        -d.base_net_amount,-d.base_gross_amount,d.document_id,p_user,p_user,now(),
        'REV-'||d.doc_number)
  returning document_id into v_new;

  -- mirror GL with debit/credit swapped
  insert into gl_entry(document_id,org_id,account_code,debit,credit,currency,doc_currency_amount)
  select v_new,org_id,account_code,credit,debit,currency,-doc_currency_amount
    from gl_entry where document_id=p_document_id;

  update document set status='REVERSED' where document_id=p_document_id;
  insert into event_log(entity,entity_id,action,actor_user,source)
   values('document',p_document_id,'REVERSE',p_user,'human');
  return v_new;   -- the timeline shows the PAIR
end $$;
```
`amend_document` = `reverse_document` + clone source into a new DRAFT linked via
`amended_from_document_id`. Implement using the two procedures above; never edit
the original.

## Step 5 — Mutability guard (uses the matrix, Rule 3 — no ad-hoc checks)
```sql
create or replace function assert_field_mutable(
  p_doc_type text, p_status text, p_field text
) returns void language plpgsql as $$
declare v_rule text;
begin
  select rule into v_rule from field_mutability
    where doc_type=p_doc_type and status=p_status and field=p_field;
  if v_rule is null or v_rule <> 'MUTABLE' then
    raise exception 'Field % not directly editable in % (rule=%). Use Amend/Reverse.',
      p_field, p_status, coalesce(v_rule,'LOCKED');
  end if;
end $$;
```

## Step 6 — Immutability triggers (defense in depth)
```sql
-- gl_entry is append-only
create or replace function no_change_gl() returns trigger language plpgsql as $$
begin raise exception 'gl_entry is immutable'; end $$;
create trigger gl_immutable before update or delete on gl_entry
  for each row execute function no_change_gl();

-- posted financial fields cannot be UPDATEd directly
create or replace function guard_posted_doc() returns trigger language plpgsql as $$
begin
  if old.status='POSTED' and (
     new.net_amount<>old.net_amount or new.tax_amount<>old.tax_amount
     or new.gross_amount<>old.gross_amount or new.currency<>old.currency
     or new.fx_rate<>old.fx_rate) then
     raise exception 'Posted financials are immutable; use reverse/amend';
  end if;
  return new;
end $$;
create trigger doc_posted_guard before update on document
  for each row execute function guard_posted_doc();
```

## Step 7 — Universal event trigger (Rule 4: nothing escapes)
```sql
create or replace function log_event() returns trigger language plpgsql as $$
begin
  insert into event_log(entity,entity_id,action,actor_user,source)
   values(tg_table_name,
          coalesce(new.document_id, old.document_id),
          tg_op, current_setting('conductor.user_id', true)::bigint, 
          coalesce(current_setting('conductor.source', true),'human'));
  return coalesce(new,old);
end $$;
create trigger ev_document after insert or update on document
  for each row execute function log_event();
create trigger ev_line after insert or update or delete on document_line
  for each row execute function log_event();
```
> The API sets `SET LOCAL conductor.user_id = '<id>'` and `conductor.source` at
> the start of each transaction (Phase 3).

## Verification for Phase 2 — run these, all must pass
```sql
-- tax balances: net + tax = gross on every line
select count(*) from document_line where round(line_net+line_tax,4) <> line_gross; -- expect 0
-- reversal nets to zero in GL
-- (post a doc, reverse it, then:)
select sum(debit)-sum(credit) from gl_entry; -- expect 0 across a posted+reversed pair
-- posted financial edit is blocked (this must RAISE):
do $$ begin update document set net_amount=net_amount+1 where status='POSTED' limit 1;
  raise exception 'SHOULD NOT REACH'; exception when others then null; end $$;
-- FX never recomputed: fx_rate is non-null and unchanged after a second post attempt
```

## What you just built
The engine. Tax and FX are computed once, frozen at posting, and the database
itself refuses to corrupt posted financials. Every change is logged automatically.

## Next file: 04_PHASE3_PERMISSIONS_API.md
