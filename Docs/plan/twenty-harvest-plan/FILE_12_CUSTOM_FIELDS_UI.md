# SESSION 12 — Custom Fields (UI)
# Files: apps/web/src (settings page + form/table rendering + api client), i18n locales

Twenty reference: the Settings → Data model screen — a non-programmer adds a field before
lunch. Ours is deliberately smaller (two entities, five types) and bilingual by construction.

---

## Before You Start

1. Read FILE_11's defs endpoint shape (`/api/custom-fields/?entity=`).
2. Open the customer create/edit form + the item form in `apps/web/src/pages/` → where dynamic
   fields render (after the fixed fields, before actions).
3. Open the unified table kit's column model (+ FILE_07 saved views config) → custom columns
   must be selectable columns like any other.

"Do not write anything yet."

---

## Task A — Settings page "الحقول المخصّصة / Custom fields"

Entity picker (customers | items) → defs list (label ar+en, type, required, active, drag to
reorder = position). Create/edit dialog: BOTH labels required (mirror of parity), type,
required, choices editor for CHOICE. Deactivate with a calm explanation of what happens to
existing data. Designed empty state: what custom fields are, one line, + create action.

## Task B — Form rendering

Customer + item forms render active defs from the endpoint: TEXT→input, NUMBER→numeric input,
DATE→existing date picker, CHOICE→existing select, MONEY→existing money input (minor units at
the edge via `lib/money.ts`). Validation errors surface per-field, human, both languages.

## Task C — Tables + views + detail

Custom fields available as optional columns in the unified table kit (and therefore inside
FILE_07 saved views). Record detail pages show non-empty custom values in the meta/details
section, label per active language.

---

## Smoke Test

- [ ] Add a CHOICE field on customers in Settings (ar labels first) → appears on the customer
      form → save value → visible on detail + as a table column → include it in a saved view
- [ ] Required violation shows a human ar/en error on the exact field
- [ ] Deactivate the def → form/table hide it; old values untouched (verify via API)
- [ ] RTL: settings page, dialogs, reorder all correct; en identical
- [ ] parity + `npx tsc -b` + gate03 green; brand-feel checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_13_ACTIVITY_TIMELINE.md in a FRESH session.
```
