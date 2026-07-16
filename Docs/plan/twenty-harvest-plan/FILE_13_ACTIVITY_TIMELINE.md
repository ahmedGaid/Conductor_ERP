# SESSION 13 — Record Activity Timeline
# Files: erp/audit/api (read-only endpoint, new), apps/web/src (record-page "النشاط" tab), i18n locales

Twenty reference: the record page timeline — every event on the record, in place. For an ERP
this is a TRUST surface: "who changed this invoice and when" answered where the argument
happens. The data already exists in the immutable audit trail; this session only exposes it.

---

## Before You Start

1. Open `erp/audit/` models + services → the exact event shape (actor, verb, entity, diff,
   correlation id, timestamp). READ-ONLY session on audit — the append-only rule is absolute.
2. Open a record detail page (sales order or invoice) → the unified page structure; where a tab
   or section slots in (unified-ui header bar + meta columns kit).
3. Open the notifications/inbox humanization (if linear-polish shipped one) → reuse the event
   wording pattern; one canonical Arabic verb per event type.

"Do not write anything yet."

---

## Task A — Read API

`/api/audit/timeline/?entity=<key>&id=<pk>` — paginated, newest first, RBAC: user must have
read permission on THAT record type (reuse module permission checks); returns actor display
name, event key, humanization params, changed-field diffs (old→new for a whitelist of
meaningful fields — not raw JSON dumps), timestamp.

## Task B — The tab

"النشاط / Activity" on customer, sales order, invoice, PO detail pages (the four
highest-dispute surfaces first). Each entry: actor, humanized sentence from an i18n key
(`audit.events.<key>` in BOTH locales), relative time (existing time formatting), small
old→new chips for changed fields (meta-chip kit). Load more pagination. Designed empty state
("لا نشاط بعد" — calm, one line). Blame-free wording throughout — the timeline states facts,
never accuses.

## Task C — Verifiability hook

Where an entry was caused by AI or import, show the existing source glyph + link (gateway trace
/ import batch) — numbers and actions stay click-verifiable (STRATEGY mechanic 4).

---

## Smoke Test

- [ ] Edit an invoice field → timeline shows actor + humanized change with old→new chips
- [ ] User without invoice read permission → endpoint 403
- [ ] AI-drafted document shows its source link in the timeline
- [ ] ar wording uses canonical lexicon verbs; en parity; RTL correct
- [ ] `pytest erp/audit` green; parity + tsc + gate03 green; brand checklist passed

---

## After This Session

```
Smoke test passed?  ← TIER 2 COMPLETE — merge checkpoint (gate:all first, then merge to main)
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_14_API_KEYS_DOCS.md in a FRESH session.
```
