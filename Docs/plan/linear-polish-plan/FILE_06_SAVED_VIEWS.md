# SESSION 6 — Saved Views
# Files: backend per-user prefs app (read first), one migration, its API; apps/web/src/ list-page filter bar + a SavedViews control; ar.json, en.json

---

## Before You Start

1. Find where per-user preferences live server-side (`identity_services.get_preferences` was
   seen in the assistant context builder — follow it) → decide: SavedView rows join that app.
2. Open one list page's filter implementation → how filters serialize (URL query params —
   confirmed by rag-plan session 08's `filters` collection). A saved view = name + module/list
   key + that query string. Nothing cleverer.
3. Open the list page's filter-bar component → where a views control naturally sits (start of
   the bar, before filter chips).

Do not write anything yet.

---

## Task A — Backend

Model in the prefs app you found (follow its conventions): `SavedView(user FK, list_key
CharField, name CharField(60), query TextField, is_default Boolean, timestamps)`, unique
`(user, list_key, name)`. API: list-by-list_key / create / rename / delete / set-default —
follow the app's existing view/router style, owner-scoped always (a user only ever sees their
own). Tests: CRUD + ownership isolation + default uniqueness per list_key.

## Task B — Frontend

Views control on the filter bar (template: sales orders list, then the same component drops
into every list already sharing that bar):

- Dropdown: "All" + user's views for this list; active view name shown; switching applies its
  query string (URL-driven — back button works free).
- "Save view" appears when current filters differ from the active view; names via the app's
  existing inline-input pattern; rename/delete in the dropdown row actions; "set default"
  star — default view auto-applies on first visit to that list.
- Empty state (no saved views yet): one quiet line, not a card.

## Task C — i18n

`views.*` keys ×2 locales. Arabic word for saved view: pick with `conductor-brand` lexicon
rules (one canonical word — check Identity System §6 first, add there if absent).

---

## Smoke Test

- [ ] `pytest` on the prefs app green (CRUD + isolation tests)
- [ ] Save a filtered view → appears in dropdown; reload → still there; switch views →
      filters + URL update
- [ ] Default view auto-applies on fresh navigation; "All" escapes it
- [ ] Second user cannot see first user's views (API probe)
- [ ] Works on at least sales + inventory lists (shared component proof)
- [ ] RTL + both locales; gates green; brand-feel check on the dropdown

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_06_SAVED_VIEWS_done.md
→ /compact → FILE_07_RECORD_TIMELINE.md (suggest /model sonnet)
```
