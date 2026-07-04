# SESSION 2 — Undo Rollout (mechanical)
# Files: purchasing / inventory / crm / accounting list+detail pages, ar.json, en.json

---

## Before You Start

1. Open `lib/useUndoableAction.ts` and ONE converted sales call-site from session 01 — this
   is the template; copy it exactly, vary nothing but names.
2. Per module, list the inverse-pair operations from its `api/` file (same exercise as
   session 01 step 3). Ops without a clean inverse are skipped — write the skip list into the
   commit message.
3. Reminder: accounting = ONLY non-financial ops (rename, archive, tag). Posting, reversal,
   reconciliation, period ops stay confirm. When unsure → skip and note.

Do not write anything yet.

---

## Task A — Convert, module by module

For purchasing → inventory → crm → accounting: apply the session-01 template to every listed
inverse-pair op. One commit per module (reviewable slices). Receipts engines
(`lib/feedback/*.ts`) keep firing where they exist.

## Task B — i18n

Per-op toast messages ×2 locales, same voice as session 01's.

---

## Smoke Test

- [ ] One undo round-trip verified per module (archive→undo or equivalent)
- [ ] Toast expiry per module → state correct after reload
- [ ] Accounting financial flows untouched (spot-check post + reverse still confirm)
- [ ] Skip list documented in commit messages
- [ ] Gates: parity, tsc, gate03 green

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_02_UNDO_ROLLOUT_done.md
→ UNDO TIER COMPLETE — merge checkpoint.
→ /compact → FILE_03_LIST_KEYBOARD_NAV.md (fresh session, /model opus)
```
