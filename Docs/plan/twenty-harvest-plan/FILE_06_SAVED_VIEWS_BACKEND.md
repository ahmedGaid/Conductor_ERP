# SESSION 6 — Saved Views (Backend)
# Files: erp/core/saved_views.py (new: model+service), erp/core/api/ (extend), migrations, erp/core/tests/test_saved_views.py (new)

Twenty reference: views are first-class records (filters, sorts, visible fields, groups per
view, shareable) — the single most-used daily power feature. Users build their own reports.

---

## Before You Start

1. **Overlap audit (mandatory):** linear-polish shipped "views" in some form. Grep
   `apps/web/src` for view/filter persistence (also check `prefs.ts` and localStorage usage —
   the ux-audit memory says some state lives there). Determine: is there ALREADY a saved-view
   concept? If yes → this session MIGRATES it server-side and extends; if it's only per-user
   local prefs → this session adds the server model and FILE_07 merges the two.
2. Open `erp/core/models.py` + one service-contract module (e.g. `erp/sales/services*`) →
   match the service-fn idiom + RBAC check pattern.
3. Open one unified-table list page's query params (`apps/web/src/api/…`) → the exact
   filter/sort/column shape the config JSON must store (store WHAT THE FRONTEND SENDS — no
   invented DSL).

"Do not write anything yet."

---

## Task A — Model

```python
class SavedView:  # owner FK, page_key (e.g. "sales.orders"), name, config JSON
                  # {filters, sort, columns, density?}, is_shared, is_default, timestamps
```

Constraints: unique (owner, page_key, name); one is_default per (owner, page_key) — enforce in
service (demote the previous default, same pattern as the pricing default fix in
`test_resolve.py::test_set_single_default_demotes_other_defaults`).

## Task B — Service contract + API

`create_view / update_view / delete_view / set_default / list_views(actor, page_key)`.
Rules: owner edits/deletes own; `is_shared=True` views readable org-wide, editable by owner or
admin role only. Config is validated as opaque-but-bounded JSON (size cap, known top-level keys)
— the frontend owns the semantics. DRF endpoints under `/api/views/` (register in root urls).

## Task C — Tests

CRUD + permissions (non-owner edit → 403); shared visible to second user; default demotion;
config size cap; page_key isolation.

---

## Smoke Test

- [ ] `pytest erp/core` green
- [ ] Overlap-audit finding written into the commit message (what existed, what this extends)
- [ ] gate17 (if FILE_03 done) passes with the ADDED routes noted, nothing broken

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_07_SAVED_VIEWS_UI.md in a FRESH session.
```
