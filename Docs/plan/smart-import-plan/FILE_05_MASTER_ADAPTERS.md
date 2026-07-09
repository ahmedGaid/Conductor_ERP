# SESSION 5 — Master-Data Adapters
# Files: erp/imports/adapters/__init__.py, adapters/crm.py, adapters/purchasing.py, adapters/inventory.py, adapters/pricing.py (all new), erp/imports/tests/test_adapters.py (new)

> Model note: Sonnet fits this session — repeating one pattern eight times against known
> write-paths. The FIRST adapter (customers) sets the pattern; copy it.

---

## Before You Start

1. Open the real write-paths and READ their signatures — do not guess:
   - customers/contacts → `erp/crm/services/` (find the create-customer function)
   - suppliers → `erp/purchasing/services/`
   - items, categories, warehouses, units of measure → `erp/inventory/services/`
   - price lists → `erp/pricing/services/`
   If a module has NO service create-function for an entity (model-only), STOP for that entity:
   record a blocker in erp-status naming the module — the module owner adds the service first
   (never write ORM creates from the imports app).
2. Open `erp/imports/registry.py` → FieldSpec/ImportAdapter protocol.
3. Open FILE_03's synonym seed list → those synonyms live HERE, in each adapter's FieldSpecs.

"Do not write anything yet."

---

## Task A — One adapter per entity

Eight adapters: `customers`, `suppliers`, `items`, `item_categories`, `warehouses`, `units`,
`price_lists`, `contacts`. Each declares:

- `fields`: FieldSpecs with en+ar synonyms (name, code, phone, email, tax_id, address,
  opening_balance… per entity — mirror the write-path's parameters, required flags from it).
- `natural_key`: customers → name+phone (fallback name); items → sku (fallback name+unit);
  suppliers → tax_id (fallback name); warehouses/units/categories → name.
- `lookup(actor, field, value)`: resolve refs (item→category/unit; customer→price list) with
  normalized-name matching (session 4 text pass) — actor-scoped querysets ONLY.
- `exists(actor, row)`: natural-key fetch, actor-scoped.
- `write(actor, row)`: call the module service function. Nothing else. No try/except-pass.
- `group_by = None` (masters are one-row-one-record).

Register all eight in `adapters/__init__.py`; app `ready()` imports it.

## Task B — Configurable defaults (spec step 7 groundwork)

Each adapter exposes `defaults` (e.g. items: default category "غير مصنف", default unit) read
from a single `IMPORTS_DEFAULTS` setting dict — used in session 8's auto-create. Add the
setting with sensible values; every key documented in one comment block.

## Task C — Tests

Per adapter: happy-path write creates via the service (assert the real record + audit side
effects the service already does); `exists` hits on natural key after normalize; ref lookup
resolves Arabic-spelling variants; unpermitted actor → the service's own PermissionError
propagates (engine does not swallow it).

---

## Smoke Test

- [ ] All 8 entities registered; `registry.get("customers").write(actor, row)` creates a real customer
- [ ] Item row with category name in Arabic variant spelling resolves to the existing category
- [ ] Unpermitted actor blocked by the module's own check
- [ ] No `objects.create` on module models anywhere in `erp/imports/adapters/`
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_06_ANALYZE_VALIDATE.md in a FRESH session.
```
