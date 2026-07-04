# SESSION 3 — Universal List Keyboard Nav + Template Module
# Files: apps/web/src/lib/useListNav.ts (new), one sales list page, app/ShortcutsDialog.tsx, ar.json, en.json

---

## Before You Start

1. Open the CRM Leads/Tickets keyboard-nav implementation (shipped in PR #12 — grep
   `keydown` or `onKeyDown` under `pages/crm`) → read it fully. The task is to EXTRACT this
   into a shared hook, not invent a second behaviour.
2. Open the existing bulk-select implementation on lists (shipped on main) → note its
   selection state shape — `x` must drive THIS selection, not a parallel one.
3. Open `app/ShortcutsDialog.tsx` → how shortcuts are registered/documented.
4. Check focus management: how lists render rows (table? virtualized?) and how the ⌘K palette
   and assistant panel (⌘J) claim keyboard focus — the hook must go inert when any
   overlay/input has focus.

Do not write anything yet.

---

## Task A — `useListNav` in `lib/useListNav.ts`

Extract the CRM behaviour into one hook:

- `j`/`k` (and ArrowDown/Up) — move active row; visible focus ring (existing focus token);
  scrolls into view; RTL-safe (vertical only, no left/right assumptions).
- `enter` — open active row (same handler as row click).
- `x` — toggle active row in the EXISTING bulk-select state.
- `esc` — clear selection, then blur active state.
- Inert whenever: an input/textarea/contenteditable has focus, a dialog/palette/panel is open.
- Honour reduced-motion for the scroll behaviour.

API sketch — adjust to what the CRM code actually needs:

```ts
useListNav({ rowCount, onOpen(index), selection?: {toggle(index)}, enabled })
```

Refactor the CRM pages to consume the hook (behaviour identical — this is the proof the
extraction is faithful).

## Task B — Template wiring (sales lists)

Wire the hook into the sales list pages. Active-row style: existing hover/selected tokens,
monochrome.

## Task C — Document the keys

Add j/k/enter/x/esc to `ShortcutsDialog` (both locales).

---

## Smoke Test

- [ ] CRM lists behave exactly as before (extraction regression)
- [ ] Sales lists: full j/k/enter/x/esc flow, keyboard only, both LTR and RTL
- [ ] Typing in the list's search/filter input → keys type, nav inert
- [ ] ⌘K open → nav inert; close → nav resumes
- [ ] Shortcuts dialog lists the keys in both languages
- [ ] Gates green; brand-feel check on focus ring (calm, visible, token-based)

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_03_LIST_KEYBOARD_NAV_done.md
→ /compact → FILE_04_KEYBOARD_ROLLOUT.md (suggest /model sonnet)
```
