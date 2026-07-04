# SESSION 4 — Keyboard Nav Rollout (mechanical)
# Files: purchasing / inventory / accounting / remaining list pages

---

## Before You Start

1. Open `lib/useListNav.ts` + one wired sales list from session 03 — the template.
2. List every list page not yet wired: grep the shared list/table component's usages, or walk
   `pages/` per module. Write the checklist first.

Do not write anything yet.

---

## Task A — Wire every remaining list

Module by module (one commit each): purchasing, inventory, accounting, plus any admin/settings
lists using the same list component. Vary nothing but names. A page whose rows have no detail
route wires `onOpen` to its existing primary row action (or omits enter — note it).

---

## Smoke Test

- [ ] Keyboard-only walkthrough: one list per module, full j/k/enter/x/esc, RTL checked
- [ ] No page broke bulk-select or row click (spot-check per module)
- [ ] Checklist from step 2 fully ticked in the commit messages
- [ ] Gates: tsc, gate03 green (no new strings expected — parity trivially green)

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_04_KEYBOARD_ROLLOUT_done.md
→ KEYBOARD TIER COMPLETE — merge checkpoint.
→ /compact → FILE_05_PEEK_PANELS.md (fresh session, /model opus)
```
