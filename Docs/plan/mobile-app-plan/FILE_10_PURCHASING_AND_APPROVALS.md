# SESSION 10 — Purchasing & Approvals Inbox
# Files: apps/mobile/app/(tabs)/inbox/**, apps/mobile/app/(tabs)/more/purchasing/**,
#        apps/mobile/src/api/endpoints/purchasing.ts, workflow.ts (new)

**Objective:** purchasing (suppliers, purchase orders, receiving hook) plus the screen mobile is
BORN for: the **approvals inbox** — every pending workflow approval in one list, swipe to approve
with undo, full document context one tap away. A manager should clear approvals from a taxi.

---

## Before You Start

1. Open web purchasing pages + `apps/web/src/api` purchasing module → endpoints, PO statuses,
   receiving flow shape.
2. Open `erp/workflow/` API (find how web lists/actions pending approvals) → the approvals
   contract: list, approve, reject, comment. Note idempotency behaviour of the approve endpoint
   (approving an already-approved doc must be safe — verify; if not, note for session 16).
3. Open `erp/purchasing/contracts/__init__.py` (read-only) → server truth recap.
4. Session 08 patterns + session 09's FormScreen/draft mechanics.

"Do not write anything yet."

---

## Task A — Approvals inbox (`inbox/`)

1. List: grouped by document type, newest first (or web's order — READ it). Each row: doc type
   icon (own set), title ("أمر شراء ٤٥٢ — مورد النور"), amount (money variant), requester +
   relative time, urgency only if the workflow model has it.
2. **Swipe actions** (build a `SwipeableRow` in patterns — RN gesture via the built-in
   Pressable/PanResponder or the navigator's swipeable if already available; NO new gesture dep
   without DECISIONS): swipe-end = approve (monochrome check + word), swipe-start = reject
   (opens comment Sheet — rejection always carries a reason, matching web's workflow rules).
3. Approve = optimistic: row slides out + Toast with UNDO (5 s window; undo calls the reverse
   only if the workflow supports it — READ; if irreversible, NO optimistic slide: confirm Dialog
   instead. Never fake reversibility).
4. Row tap → approval detail: the document's RecordScreen with an approval action bar (approve /
   reject / comment / open full record). Approving from detail returns to a list that has
   already moved on — calm, no full reload.
5. Empty state is a designed moment ("لا يوجد ما يحتاج موافقتك" + subtle icon) — this screen is
   seen daily; it must feel good empty.
6. Badge: tab icon shows pending count (from the list endpoint's count; session 15 keeps it live
   via push).

## Task B — Suppliers & POs (`more/purchasing/`)

1. Suppliers: ListScreen + RecordScreen + create/edit via FormScreen — mirror session 09's
   customer build exactly (same patterns; this should be FAST).
2. PO ListScreen (status FilterSheet) + PO RecordScreen: lines, totals, receiving status per
   line, related invoice/GRN links, per-status actions mirroring web.
3. PO create via FormScreen + drafts — same shape as invoice create, purchasing endpoints.
4. Receiving: from a PO, "استلام" flow — quantities-received editor per line (numeric steppers,
   barcode hook stub for session 11), submit through the same receiving endpoint web uses.
   Partial receiving must match web behaviour precisely.

---

## Smoke Test

- [ ] Two-device test: create a PO needing approval (from web), it appears in mobile inbox
      (pull-to-refresh; push comes in session 15) → swipe-approve → web shows approved, audit
      shows the mobile user
- [ ] Undo within 5 s → document back to pending everywhere (or, if irreversible, confirm-Dialog
      path verified instead — whichever Task A.3 established)
- [ ] Reject requires a comment; comment lands on web's workflow trail
- [ ] Approve something already approved elsewhere (race) → calm designed message, list refreshes
      — no crash, no double action
- [ ] PO create + partial receive from phone → stock/PO state identical to doing it on web
- [ ] Swipe directions correct in RTL (end/start, not left/right); empty inbox state shown
- [ ] tsc + parity green; PARITY.md purchasing/approvals rows flipped

## Risks

- Optimistic approve on a non-idempotent endpoint → the Before-You-Start idempotency check
  decides optimistic vs confirm; when unsure, confirm.
- Swipe gesture vs list scroll conflicts → generous activation distance; test on a cheap Android
  device, not just flagships.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_11_INVENTORY_AND_BARCODE.md
```
