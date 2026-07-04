# SESSION 8 — Notifications Inbox
# Files: erp/notifications API additions, apps/web/src inbox surface + app-frame entry, ar.json, en.json

---

## Before You Start

1. Open `erp/notifications/` models + API → what exists: `Notification` rows (channel,
   recipient, status, reference…) are outbound dispatch logs. Determine whether an IN-APP
   channel / per-user notification concept exists, or only email/etc. dispatch. THIS decides
   scope:
   - If an in-app channel exists → inbox = its reader.
   - If not → add `read_at` (nullable) + a per-user queryset over notifications whose
     recipient is the user, for an "inapp" channel adapter that just stores rows. Read
     `adapters/` to add it the way other adapters register.
2. Open the app frame (`app/AppShell.tsx`) → where a bell entry sits in the chrome
   (monochrome — the icon carries an unread dot only, using the existing accent-dot pattern
   if one exists; no red badge counts).
3. Check what events currently dispatch notifications (grep `dispatch(` callers) → the inbox
   is only as alive as its sources; list which events will land in it.

Do not write anything yet.

---

## Task A — Backend

Per the step-1 finding (keep additive): "inapp" adapter (stores, always ok), `read_at` field +
migration, endpoints: list mine (unread first, cursor), mark read, mark all read. Tests:
isolation (only mine), read transitions, adapter registers like the others.

## Task B — Inbox surface

Panel from the bell (same overlay pattern as the assistant panel/⌘K — reuse): rows = subject,
one-line body, source module word, relative time; unread = weight difference not colour;
click → navigates via `reference` (reuse the reference→route mapping if one exists — check
how receipts link) and marks read. "Mark all read" at top. Designed empty state ("All caught
up" — quiet, both languages). j/k/enter work inside (reuse `useListNav`).

## Task C — i18n

`inbox.*` keys ×2 locales.

---

## Smoke Test

- [ ] Trigger an event that dispatches (e.g. workflow escalation from seed/demo flow) → bell
      dot appears; open → row present, unread
- [ ] Click row → navigates to the record, row marked read, dot clears when none left
- [ ] Mark all read works; empty state shows
- [ ] Second user sees only their rows
- [ ] Keyboard-only pass inside the panel; RTL correct
- [ ] `pytest erp/notifications` + gates green; brand-feel check (calm, no red noise)

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_08_NOTIFICATIONS_INBOX_done.md
→ SURFACES TIER COMPLETE — merge checkpoint.
→ /compact → FILE_09_NUMBER_TYPOGRAPHY.md (fresh session)
```
