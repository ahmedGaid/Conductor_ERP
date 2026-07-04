# SESSION 7 — Per-Record Activity Timeline
# Files: one backend audit-read API (if missing), apps/web/src/components/RecordTimeline.tsx (new), detail pages wiring, ar.json, en.json

---

## Before You Start

1. Open `erp/audit/` services + the assistant's `_document_history` tool runner
   (`erp/assistant/tools.py`) → the query shape for "entries for entity_type + entity_id"
   already exists; check whether a REST endpoint exposes it to the web app yet.
2. Open one detail page (sales order) → find where secondary content sits (side column?
   bottom section?) and how it lazy-loads.
3. Audit rows: read the actual `before/after/action/actor/created_at` shape — the timeline
   renders WORDS from it, not raw JSON.

Do not write anything yet.

---

## Task A — Read API (only if missing)

Additive endpoint (place it with the audit or core API views, following their style):
`GET /api/audit/history?entity_type=&entity_id=` → last 30 entries, permission = user must
have read access to that module (reuse the existing module-access check the app uses
everywhere). Never expose other modules' entries. Tests: shape + module-access denial.

## Task B — `RecordTimeline.tsx`

Quiet vertical list, newest first: actor display name, human verb (map `action` codes →
translated phrases: created / updated / posted / archived…), relative time (existing date
util), and for updates a compact "field: old → new" line ONLY for human-meaningful fields
(skip ids/timestamps — keep a small skip-set). Collapsed to last 5 with "show all".
Designed empty state ("No activity yet" done properly). Loading skeleton. Blame-free tone —
the timeline states facts, never "user X broke Y".

## Task C — Wiring

Template: sales order detail. Then the same component on customer, supplier, item, invoice,
journal detail pages (each = one line of wiring; do all in this session — the component is the
work, wiring is trivial).

## Task D — i18n

`timeline.*` verbs + labels ×2 locales.

---

## Smoke Test

- [ ] Edit an order, revisit detail → edit appears with actor + field change in plain words
- [ ] User without accounting access probes a journal's history endpoint → denied
- [ ] Empty timeline state designed (new record)
- [ ] "Show all" expands; collapsed by default
- [ ] RTL: timeline rail on inline-start, reads naturally in Arabic
- [ ] Backend tests + gates green

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_07_RECORD_TIMELINE_done.md
→ /compact → FILE_08_NOTIFICATIONS_INBOX.md (/model opus)
```
