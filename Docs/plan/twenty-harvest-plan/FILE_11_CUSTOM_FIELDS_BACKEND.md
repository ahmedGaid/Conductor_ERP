# SESSION 11 — Custom Fields (Backend) — fields only, NEVER objects
# Files: erp/core/custom_fields.py (new: model+service+validation), migrations (JSONB columns on sales.Customer + inventory.Item), touched module services (validation hook), tests

Twenty reference: their metadata engine lets users add fields in a minute — the part of the
platform story worth having. We take custom FIELDS only; custom OBJECTS stay refused
(STRATEGY §5 — configurability is Odoo's disease). Scope brake: if a session finds itself
generalizing toward dynamic entities, STOP.

---

## Before You Start

1. Open `erp/sales/` Customer model + its `create_customer`/update service fns → where a
   validation hook slots in without changing the fn SIGNATURES.
2. Open `erp/inventory/` Item model + services → same.
3. Open one XLSX export path (reports) → where custom columns append.
4. Open the audit service → field-level changes on custom_data must audit like real fields.

"Do not write anything yet."

---

## Task A — Definitions

```python
class CustomFieldDef:  # entity_key ("sales.customer" | "inventory.item"), key (slug, immutable),
                       # label_ar, label_en, type (TEXT|NUMBER|DATE|CHOICE|MONEY),
                       # required, choices (list, for CHOICE), is_active, position, timestamps
```

Service fns (admin-only): create/update/deactivate — never hard-delete a def that has data;
deactivate hides it, values stay. Both labels REQUIRED (parity is backend-enforced too).

## Task B — Values

One migration per entity: `custom_data = JSONField(default=dict)` on Customer and Item (start
with exactly these two; expansion later is mechanical). Validation module
`validate_custom_data(entity_key, data) -> cleaned`: unknown keys rejected; type coercion
(MONEY = integer minor units; DATE = ISO; NUMBER = int/Decimal-as-str); required enforced;
CHOICE membership. Called from inside the existing service create/update fns (hook, not
signature change). Serializers expose `custom_data` + the active defs endpoint
(`/api/custom-fields/?entity=`) so the frontend renders from truth.

## Task C — Export + audit

XLSX export for these entities appends active custom fields as columns (label per the export's
language). Audit entries record custom_data diffs per key like normal field changes.

## Task D — Tests

Def CRUD permissions; required/type/choice validation errors are human + blame-free; MONEY kept
integer; deactivated def keeps old values readable but rejects new writes; export includes the
column; audit diff present.

---

## Smoke Test

- [ ] Define "منطقة التوصيل / Delivery zone" (CHOICE) on customer via service → create customer
      with a valid + an invalid value → correct outcomes
- [ ] MONEY custom field stores integers; export shows formatted value
- [ ] `pytest erp/core erp/sales erp/inventory` green; gate17 notes additive routes only

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_12_CUSTOM_FIELDS_UI.md in a FRESH session.
```
