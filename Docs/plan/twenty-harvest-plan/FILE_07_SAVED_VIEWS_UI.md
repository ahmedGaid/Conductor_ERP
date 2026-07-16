# SESSION 7 — Saved Views (UI)
# Files: apps/web/src (unified table kit + new api/views.ts + list pages), i18n locales

Twenty reference: saved views render as TABS above every list — the user's own workspaces
inside a module. Switching is instant; sharing is one toggle.

---

## Before You Start

1. Re-read FILE_06's overlap-audit conclusion (commit message) — build on exactly that.
2. Open the unified table kit (sales>orders is the reference implementation per unified-ui
   plan) → where filters/sorts/columns state lives today and how a page declares its `page_key`.
3. Open `apps/web/src/prefs.ts` → active-view-per-page persistence goes here (local), view
   DEFINITIONS come from the server (FILE_06).

"Do not write anything yet."

---

## Task A — View tabs row

Above the unified table: tabs = [الكل/All] + user's views + shared views (marked with the
existing "shared" glyph from `icons.tsx` — no new icon hand). Active tab = applied config.
`+` tab → "save current view" (name dialog, ar/en). Overflow → ⋯ menu (rename, share toggle,
set default ★, delete with confirm). Logical CSS; tab order flows start→end (RTL-correct).

## Task B — Apply/save loop

Current table state (filters/sorts/columns) diffed against active view → subtle "unsaved
changes" dot on the tab + "save / save as new / reset" in the ⋯ menu. Optimistic updates with
toast + undo (existing primitives). Default view auto-applies on page entry.

## Task C — Rollout

Wire sales>orders first (the kit's reference page), then the remaining list pages through the
kit — if the kit is truly unified this is config, not per-page code. Any page that can't take
it → note the gap in the commit, don't fork the kit.

Arabic term check: one canonical word for "view" (Identity System §6) — add BEFORE shipping.

---

## Smoke Test

- [ ] Create/rename/share/default/delete a view on sales>orders — all optimistic, all undoable
- [ ] Second browser (second seeded user): shared view visible, private one not
- [ ] Switch view → table state applies instantly; reload → default view active
- [ ] RTL: tab order, dialogs, ⋯ menus all correct in Arabic; en identical
- [ ] parity + `npx tsc -b` + gate03 green; conductor-brand brand-feel checklist passed

---

## After This Session

```
Smoke test passed?  ← TIER 1 COMPLETE — merge checkpoint (gate:all first, then merge to main)
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_08_COMMAND_MENU_ACTIONS.md in a FRESH session.
```
