# SESSION 12 — ⌘K ↔ AI Bridge
# Files: apps/web/src/app/CommandBar.tsx, the assistant panel opener (AssistantProvider), ar.json, en.json

---

## Before You Start

1. Open `app/CommandBar.tsx` → read the full match pipeline (page actions + live server
   search from PR #12) and what renders when NOTHING matches.
2. Open the assistant panel opener (grep `⌘J` handler / `AssistantProvider`) → find the
   programmatic "open panel with a prefilled question" path; if the panel can't yet open
   with an initial message, add that capability (additive prop/event).

Do not write anything yet.

---

## Task A — The fallthrough row

In the palette's result list, when the query looks like a question or has no command/record
match (heuristic: no matches, OR query > 3 words, OR ends with ؟/?), append one final row —
always LAST, never preempting real matches:

> ✳ Ask Conductor AI: "<query>"    — t("commandBar.askAi")

Enter on it (or click) → close palette → open assistant panel with the query submitted as the
message (the panel's normal flow takes over: steps, answer, citations). Icon from the
existing single-stroke set (the assistant's existing glyph — reuse).

## Task B — i18n + shortcut docs

`commandBar.askAi` ×2 locales; ShortcutsDialog note if the dialog documents palette rows.

---

## Smoke Test

- [ ] Type "كم فاتورة متأخرة عندنا" in ⌘K → AI row appears → enter → panel opens, question
      already running
- [ ] Type "orders" → normal matches first, AI row last (or absent when matches are strong —
      per your heuristic; be consistent)
- [ ] Esc chain sane: palette closes, panel stays; esc again closes panel
- [ ] Assistant disabled (`/status` off) → AI row never renders
- [ ] RTL rendering of the row correct; gates green

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_12_CMDK_AI_BRIDGE_done.md
→ /compact → FILE_13_ACCEPTANCE.md
```
