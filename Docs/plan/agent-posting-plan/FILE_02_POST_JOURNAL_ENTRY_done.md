# SESSION 02 — Post a drafted journal entry (new domain gap, closed for both human and assistant)
# Files: erp/accounting/services/posting.py, erp/accounting/api/views.py, erp/accounting/urls.py,
#        erp/accounting/api/serializers.py, apps/web/src/api/accounting.ts,
#        apps/web/src/pages/accounting/JournalDetailPage.tsx,
#        erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        erp/accounting/tests/test_posting.py, ar.json / en.json

**Model:** Opus. New GL-affecting domain code (not a thin wrapper) — same caliber as the original
agent-actions FILE_04. Requires FILE_01 done (`_can_post`/`challenge` guard live).

---

## Before You Start

1. Read `FILE_00_INDEX.md`'s "discovered gap" note — the reasoning for why this needs new code.
2. Read `erp/accounting/services/posting.py` in full: `post_journal` (creates fresh, always
   `POSTED`), `reverse_journal` (the only existing status-mutating transition on an existing entry —
   the closest precedent for this session's new function), `enforce_journal_approval` (a **view-layer**
   call today, not inside `post_journal` itself — `JournalListPostView.post` calls it before
   `services.post_journal`; this session's new manual view AND the assistant action's `execute` must
   each call it too, in the same place, for the same reason: neither goes through the other).
3. Read `erp/accounting/api/views.py` `JournalListPostView` and `JournalDetailView` (`_CanAccount`
   permission, `_scoped`/`_LINES_PREFETCH` patterns) — the new manual endpoint follows them exactly.
4. Read `erp/accounting/contracts/__init__.py` `find_journal` (locates entries by number/reference/
   memo) and confirm whether it already returns `DRAFT` entries or needs a status param added —
   check its actual query, not just its docstring (the docstring says "posted" but the filter shown
   in this plan's design phase did not visibly restrict by status — verify before relying on it).
5. Read `apps/web/src/pages/purchasing/PurchaseRequestDetailPage.tsx` lines ~55–168 — the exact
   `primaryAction()`/`barPrimary`/`useSetPageActions({ primary, menuItems })` template for adding a
   status-gated primary button to a detail page (`DocumentPrimary`, `DocumentPrimaryButton`,
   optimistic `act()` helper). `JournalDetailPage.tsx` currently has NO primary (comment: "a posted
   journal is read-only — no lifecycle primary") — this session adds the first one, gated on
   `status === "draft"` only.
6. Read `erp/assistant/services/actions.py` `_build_journal_entry`/`_execute_journal_entry` (the
   existing DRAFT-creating action) and `_can_post`/`challenge` (added in FILE_01).

"Do not write anything yet."

---

## Task A — `post_draft_journal_entry()` service

In `erp/accounting/services/posting.py`, next to `reverse_journal`:

- Signature: `post_draft_journal_entry(entry: JournalEntry, actor=None) -> JournalEntry`.
- Guard: `entry.status != EntryStatus.DRAFT` → raise `AlreadyPostedError` (same error `reverse_journal`
  raises for the opposite direction — reuse, don't invent a new error class).
- Re-validate what may have changed since the draft was created: `entry.period` may have closed
  (`if not entry.period.is_open: raise ClosedPeriodError`), each line's account may have been
  deactivated (`if not (line.account.is_postable and line.account.is_active): raise
  NonPostableAccountError`) — reuse `_validate_and_load_accounts`'s account-check logic pattern,
  don't re-derive it from scratch if a shared helper can serve both.
- Flip: `status = EntryStatus.POSTED`, `posted_at = timezone.now()`, `posted_by = actor if
  authenticated else None`.
- Same audit + event as `post_journal`: `audit.record(module="accounting", action="post_journal",
  ...)` (reuse the same action name — it IS the same business event, just from a draft) and
  `bus.publish(events.JOURNAL_POSTED, {...})`.
- `@transaction.atomic`, matching every other posting function in this file.

## Task B — manual "Post" button

- `erp/accounting/api/serializers.py`: none needed (no request body — the id is in the URL).
- `erp/accounting/api/views.py`: new `JournalPostDraftView(APIView)`, `permission_classes =
  [IsAuthenticated, _CanAccount]` (same as `JournalDetailView`), `post(self, request, entry_id)`:
  load the scoped entry (404 if out of scope, same `_scoped` helper), call
  `services.enforce_journal_approval(request.user, sum(line debits))` then
  `services.post_draft_journal_entry(entry, actor=request.user)`, return the serialized entry.
- `erp/accounting/urls.py`: mount at `journals/<uuid:entry_id>/post` (mirrors how purchasing mounts
  `orders/<id>/receive` etc. — check that file for the exact URL-pattern style already used here).
- `apps/web/src/api/accounting.ts`: `export function postDraftJournalEntry(id: string):
  Promise<JournalEntry> { return apiFetch<JournalEntry>(\`/accounting/journals/${id}/post\`, {
  method: "POST", body: "{}" }); }`.
- `apps/web/src/pages/accounting/JournalDetailPage.tsx`: add `primaryAction()` returning `{ label:
  t("accounting.entry.post"), onClick: () => act(...) }` when `data.status === "draft"`, `null`
  otherwise (matches the `PurchaseRequestDetailPage` template — copy its optimistic `act()` shape,
  adapted to a single terminal transition with no follow-up receipt card needed). Wire
  `useSetPageActions({ primary: barPrimary, menuItems: barMenu })` (the page already publishes
  `barMenu`; add `barPrimary` alongside it, currently absent). New i18n keys: `accounting.entry.post`,
  `accounting.entry.toastPosted`.

## Task C — `post_journal_entry_draft` assistant action

In `erp/assistant/services/actions.py`:

- `_build_post_journal_entry(actor, *, query=None, **_)`: `if not _posting_enabled(): return
  _refused_posting_disabled()`; `if not _can(actor, ACCOUNTANT, BRANCH_MANAGER): return
  _refused()` (the two-step check FILE_01 specifies — accurate message either way). Use
  `accounting.find_journal(actor, query=query)` filtered to `status == "draft"` entries (client-side
  filter per Before-You-Start point 4's finding) to resolve `query`; `{"error": ...}` if none/many
  match (mirror `convert_quotation`'s not-found/ambiguous phrasing). Proposal summary shows the
  entry's lines/total; `"challenge": challenge(<sum of debit lines>)`.
- `_execute_post_journal_entry(actor, payload)`: `if not _can_post(actor, ACCOUNTANT,
  BRANCH_MANAGER): raise PermissionError`; look the entry back up by id from the payload; call
  `accounting.enforce_journal_approval(actor, total)` then
  `accounting.post_draft_journal_entry(entry, actor=actor)` (add both to
  `erp/accounting/contracts/__init__.py`'s `__all__` re-exports — `actions.py` imports through
  `contracts`, not `services`, everywhere else in this file; follow that, don't reach into
  `services` directly for this one action).
- Register in `ACTIONS`: `name="post_journal_entry_draft"`, `kind="post"`, `risk="post"`,
  `effects=(Effect("journal_entry", "update", gl="posts"),)`, `invariants=("journal_balanced",
  "period_open")`, `requires_confirm=True` (already true by default).
- `ACTION_ARG_FIELDS` already includes `query` — no change needed there.

## Task D — tests

- `erp/accounting/tests/test_posting.py`: `post_draft_journal_entry` — happy path (draft → posted,
  audit row, event published); already-posted entry → `AlreadyPostedError`; period closed since
  draft creation → `ClosedPeriodError`; account deactivated since draft creation →
  `NonPostableAccountError`.
- `erp/accounting/tests/` (API): `JournalPostDraftView` — 201/200 round-trip, 403 for a role
  without `_CanAccount`, 404 for an out-of-scope entry.
- `erp/assistant/tests/test_actions.py`: proposal shows the right challenge amount; toggle off →
  refused; toggle on + wrong role → refused; toggle on + right role + right retype → posts,
  `EntryStatus.POSTED`, one audit row; double-confirm → 409 (existing single-use guard, unchanged);
  an already-posted entry queried again → calm `{error}`, no card.

---

## Smoke Test

- [ ] Manual: open a DRAFT journal entry (create one via the existing assistant draft action or
      seed data) → "Post" primary button appears → click → entry now shows `posted`, button gone,
      trial balance reflects it
- [ ] Assistant: "post journal entry JE-2026-…" (org toggle OFF) → calm refusal, no card
- [ ] Toggle ON, ask again → card with challenge amount → wrong retyped amount → 400, card still
      pending → right amount → confirms → entry `posted`, one audit row, card shows link
- [ ] Asking to post an already-posted entry → calm `{error}`, no card
- [ ] `pytest erp/accounting erp/assistant` + i18n parity + `tsc --noEmit` + gate03 all green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_03_RECEIVE_PURCHASE_ORDER.md and continue.
```
