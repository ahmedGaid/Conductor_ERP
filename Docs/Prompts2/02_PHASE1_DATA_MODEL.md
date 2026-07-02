# Phase 1 — Data Model
# LOW RISK — additive DDL only. This schema *encodes* the golden rules so the
# upper layers cannot violate them by accident.

Honor: Rule 1 (money is typed), Rule 2 (permission), Rule 3 (state), Rule 4 (events).

## What you will do
1. Create reference + multi-currency + tax tables.
2. Create party/item/warehouse master tables.
3. Create the document core (header + lines) with **typed money** and **state**.
4. Create GL/subledger entries (immutable).
5. Create the RBAC tables (roles, permissions, field grants, data scope).
6. Create the `event_log` traceability spine + `ai_suggestion`.

Write each as a numbered migration in `db/migrations/`. SQL below is PostgreSQL;
Oracle notes inline. **Keep names identical across DBs.**

---

## Migration 001 — reference & money
```sql
-- db/migrations/001_reference.sql
create table org (                       -- legal entity / operating unit (multi-org)
  org_id        bigint primary key generated always as identity,
  code          text not null unique,
  name          text not null,
  base_currency char(3) not null,        -- functional currency of this org
  tax_country   char(2) not null         -- e.g. 'EG'
);

create table currency (
  code        char(3) primary key,       -- ISO 4217
  minor_units smallint not null          -- EGP=2, JPY=0 — never assume 2
);

-- Daily/corporate FX, EBS GL_DAILY_RATES style. Frozen rates captured per-doc.
create table fx_rate (
  from_ccy  char(3) not null references currency,
  to_ccy    char(3) not null references currency,
  rate_date date    not null,
  rate_type text    not null,            -- 'CORPORATE','SPOT', etc.
  rate      numeric(18,8) not null,
  primary key (from_ccy, to_ccy, rate_date, rate_type)
);
```
> Oracle: `generated always as identity` is supported 12c+. `text` → `varchar2(...)`.
> `numeric` → `number`.

## Migration 002 — tax engine tables (NO rates in code, ever)
```sql
-- db/migrations/002_tax.sql
create table tax_jurisdiction (
  jurisdiction_id bigint primary key generated always as identity,
  country         char(2) not null,
  name            text not null
);

create table tax_code (
  tax_code_id     bigint primary key generated always as identity,
  jurisdiction_id bigint not null references tax_jurisdiction,
  code            text not null,         -- 'VAT_STD','VAT_ZERO','WHT_PRO'
  kind            text not null check (kind in ('VAT','WHT','EXEMPT')),
  rate            numeric(9,6) not null, -- 0.140000 ; data, not code
  is_inclusive    boolean not null default false,
  effective_from  date not null,
  effective_to    date,                  -- null = open
  unique (jurisdiction_id, code, effective_from)
);

-- Resolution rules: which tax_code applies for an item+party+place+date.
create table tax_rule (
  tax_rule_id     bigint primary key generated always as identity,
  jurisdiction_id bigint not null references tax_jurisdiction,
  item_category   text,                  -- null = any
  party_class     text,                  -- null = any ('EXPORT','LOCAL'...)
  tax_code_id     bigint not null references tax_code,
  priority        int not null default 100  -- lower wins
);
```

## Migration 003 — masters
```sql
-- db/migrations/003_masters.sql
create table party (
  party_id   bigint primary key generated always as identity,
  org_id     bigint not null references org,
  kind       text not null check (kind in ('CUSTOMER','SUPPLIER','BOTH')),
  name       text not null,
  party_class text,                      -- feeds tax_rule
  credit_limit_amount numeric(18,4),     -- typed money: paired ccy below
  credit_limit_ccy    char(3) references currency
);

create table warehouse (
  warehouse_id bigint primary key generated always as identity,
  org_id       bigint not null references org,
  code         text not null,
  name         text not null,
  unique (org_id, code)
);

create table item (
  item_id      bigint primary key generated always as identity,
  org_id       bigint not null references org,
  sku          text not null,
  name         text not null,
  item_category text,                    -- feeds tax_rule
  -- cost is SENSITIVE (drives margin). Permission gates exposure (Phase 3).
  std_cost_amount numeric(18,4),
  std_cost_ccy    char(3) references currency,
  unique (org_id, sku)
);

create table item_stock (
  item_id      bigint not null references item,
  warehouse_id bigint not null references warehouse,
  qty_on_hand  numeric(18,4) not null default 0,
  primary key (item_id, warehouse_id)
);
```

## Migration 004 — document core (typed money + frozen FX + state)
```sql
-- db/migrations/004_document.sql
create table doc_type (
  doc_type   text primary key,           -- 'SALES_ORDER','INVOICE',...
  is_financial boolean not null          -- does posting hit GL?
);

create table document (
  document_id   bigint primary key generated always as identity,
  doc_type      text   not null references doc_type,
  org_id        bigint not null references org,
  party_id      bigint not null references party,
  doc_number    text,                    -- assigned at posting
  status        text   not null default 'DRAFT'
                 check (status in ('DRAFT','POSTED','REVERSED','AMENDED')),
  -- typed money: document currency + FROZEN rate to org base ccy
  currency      char(3) not null references currency,
  fx_rate       numeric(18,8),           -- captured at POST; null while DRAFT
  fx_rate_date  date,
  fx_rate_type  text,
  -- computed totals (written ONLY by the engine in Phase 2)
  net_amount    numeric(18,4) not null default 0,
  tax_amount    numeric(18,4) not null default 0,
  gross_amount  numeric(18,4) not null default 0,
  base_net_amount   numeric(18,4),       -- in org base ccy, frozen
  base_gross_amount numeric(18,4),
  -- successor links for amend/reverse (Rule 3)
  reverses_document_id   bigint references document,
  amended_from_document_id bigint references document,
  -- metadata (mutable while POSTED per matrix)
  external_ref  text,
  internal_note text,
  due_date      date,
  created_by    bigint not null,
  created_at    timestamptz not null default now(),
  posted_by     bigint,
  posted_at     timestamptz
);

create table document_line (
  line_id      bigint primary key generated always as identity,
  document_id  bigint not null references document on delete cascade,
  item_id      bigint not null references item,
  warehouse_id bigint references warehouse,
  qty          numeric(18,4) not null,
  unit_price_amount numeric(18,4) not null,   -- in document currency
  -- resolved + computed by engine (Phase 2), never entered by hand:
  tax_code_id  bigint references tax_code,
  line_net     numeric(18,4) not null default 0,
  line_tax     numeric(18,4) not null default 0,
  line_gross   numeric(18,4) not null default 0
);

-- The field-level mutability matrix. Rule 3 lives HERE as data, not as if/else.
create table field_mutability (
  doc_type text not null references doc_type,
  status   text not null,
  field    text not null,
  rule     text not null check (rule in ('MUTABLE','REQUIRES_AMEND','REQUIRES_REVERSE','LOCKED')),
  primary key (doc_type, status, field)
);
```

## Migration 005 — immutable accounting
```sql
-- db/migrations/005_gl.sql
create table gl_entry (
  gl_entry_id  bigint primary key generated always as identity,
  document_id  bigint not null references document,
  org_id       bigint not null references org,
  account_code text not null,
  -- double entry, in BASE currency (frozen)
  debit  numeric(18,4) not null default 0,
  credit numeric(18,4) not null default 0,
  currency char(3) not null references currency,
  doc_currency_amount numeric(18,4),     -- original doc-ccy amount for trace
  created_at timestamptz not null default now()
);
-- Immutability is enforced by trigger in Phase 2 (no UPDATE/DELETE on gl_entry).
```

## Migration 006 — RBAC (row + field) + traceability spine
```sql
-- db/migrations/006_rbac_events.sql
create table app_user (
  user_id bigint primary key generated always as identity,
  username text not null unique
);
create table role (
  role_id bigint primary key generated always as identity,
  code text not null unique               -- 'SALES_CLERK','ACCOUNTANT','MANAGER'
);
create table user_role (
  user_id bigint references app_user,
  role_id bigint references role,
  primary key (user_id, role_id)
);
create table permission (
  permission_id bigint primary key generated always as identity,
  code text not null unique               -- 'doc.post','doc.reverse','view.margin','view.cost'
);
create table role_permission (
  role_id bigint references role,
  permission_id bigint references permission,
  primary key (role_id, permission_id)
);
-- Field-level visibility/editability per role.
create table field_grant (
  role_id    bigint not null references role,
  entity     text not null,               -- 'document','item','party'
  field      text not null,               -- 'margin','std_cost_amount','credit_limit_amount'
  can_view   boolean not null default false,
  can_edit   boolean not null default false,
  primary key (role_id, entity, field)
);
-- Row-level scope (which orgs/warehouses a user may touch).
create table data_scope (
  user_id bigint not null references app_user,
  org_id  bigint not null references org,
  primary key (user_id, org_id)
);

-- THE TRACEABILITY SPINE — every mutation lands here (Rule 4).
create table event_log (
  event_id    bigint primary key generated always as identity,
  entity      text   not null,            -- 'document','document_line','gl_entry'
  entity_id   bigint not null,
  action      text   not null,            -- 'CREATE','UPDATE','POST','REVERSE','AMEND'
  field       text,                       -- for field-level edits
  old_value   text,
  new_value   text,
  actor_user  bigint references app_user,
  source      text not null default 'human' check (source in ('human','ai','system')),
  suggestion_id bigint,                    -- set when source='ai'
  at          timestamptz not null default now()
);

create table ai_suggestion (
  suggestion_id bigint primary key generated always as identity,
  entity text not null, entity_id bigint not null,
  kind   text not null,                   -- 'PRICE','WAREHOUSE','DISCOUNT'
  payload jsonb not null,                 -- proposed change, read-only
  status text not null default 'PROPOSED' check (status in ('PROPOSED','ACCEPTED','REJECTED')),
  accepted_by bigint references app_user,
  accepted_at timestamptz,
  created_at  timestamptz not null default now()
);
```

## Seed the matrix + reference data
```sql
-- db/seed/010_currency_tax.sql
insert into currency(code,minor_units) values ('EGP',2),('USD',2);
-- example: Egyptian standard VAT as DATA
insert into tax_jurisdiction(country,name) values ('EG','Egypt');
-- (rate is data; update when law changes — never in code)
-- db/seed/020_field_mutability.sql  (Sales Order example)
insert into field_mutability(doc_type,status,field,rule) values
 ('SALES_ORDER','DRAFT','unit_price_amount','MUTABLE'),
 ('SALES_ORDER','DRAFT','qty','MUTABLE'),
 ('SALES_ORDER','POSTED','unit_price_amount','REQUIRES_REVERSE'),
 ('SALES_ORDER','POSTED','qty','REQUIRES_REVERSE'),
 ('SALES_ORDER','POSTED','net_amount','LOCKED'),
 ('SALES_ORDER','POSTED','internal_note','MUTABLE'),
 ('SALES_ORDER','POSTED','external_ref','MUTABLE'),
 ('SALES_ORDER','POSTED','due_date','MUTABLE');
```

## Verification for Phase 1
```bash
make migrate && make seed
psql "$DB_URL" -c "\d document"          # every money col has a *_ccy or currency sibling
# Assert no money column is unpaired:
psql "$DB_URL" -tAc "
  select count(*) from information_schema.columns
  where column_name like '%_amount' and table_schema='public'
    and table_name not in (select table_name from information_schema.columns where column_name in ('currency') or column_name like '%_ccy');"
# Expect rows only where a sibling currency exists; review manually if >0.
```
All migrations apply cleanly, seeds load, `field_mutability` has the SO rows.

## What you just built
The schema that makes the golden rules structurally true: typed money, frozen FX
columns, the mutability matrix as data, RBAC with field grants, and the event spine.

## Next file: 03_PHASE2_POSTING_TAX_FX.md
