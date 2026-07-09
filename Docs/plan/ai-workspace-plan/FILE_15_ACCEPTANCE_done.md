# SESSION 15 — Acceptance, Regression, Polish, Sign-off
# Files: none new — fixes only, within files already declared in FILE_00_INDEX.md

---

## Before You Start

1. Re-read `FILE_00_INDEX.md` ground rules.
2. Start the dev backend + `apps/web` dev server; log in as (a) an admin and (b) a limited-role
   user. Test in **Arabic first**, then English.
3. Have `DECISIONS.md` and the `conductor-brand` brand-feel checklist open.

"Do not write anything yet."

---

## Full Acceptance Checklist

**Entry & shell**
- [ ] Sparkle button identical on every page; ⌘J everywhere; listed in the `?` cheat-sheet
- [ ] Floating ⇄ docked ⇄ fullscreen all work; mode + last conversation restore after reload
- [ ] Provider key removed ⇒ zero AI surfaces anywhere (button, shortcut, route, suggestions)

**Conversations**
- [ ] Create / auto-title / rename / pin / archive / delete / search — panel and fullscreen agree
- [ ] History paginates or scrolls smoothly at 50+ conversations; instant restore

**Messages**
- [ ] Markdown: bold, lists, tables, headings, inline + fenced code (LTR inside RTL), links
- [ ] Streaming with visible steps; collapse-to-summary; expand works
- [ ] Stop, retry, regenerate, edit prompt, copy, follow-up chips — all functional
- [ ] Errors are designed, blame-free, retryable; never a raw exception string

**Context**
- [ ] Panel chip tracks the open record; "this order/هذا الأمر" resolves; detach forces a clarify
- [ ] Per-module suggestion chips all fire real tools
- [ ] Assistant never asks for user/company/language/permissions it already has

**Tools & agent**
- [ ] Each catalog tool answers its question with citations; spot-check all modules
- [ ] Multi-step question chains 2+ tools; loop never exceeds bounds; vague ask ⇒ one clarify
- [ ] Limited user: every cross-permission probe refused calmly; zero data leak (try at least 5)

**Actions & import**
- [ ] All three actions: propose → confirm → draft + audit + links; dismiss inert; double-confirm 409
- [ ] Attachments: image, PDF, CSV round-trips; size/type rejections designed
- [ ] Customer CSV import end-to-end: map → preview → execute → report; re-import creates zero

**Guided detours & resume**
- [ ] Every blocker card answers all three: what's wrong, fastest fix, how we continue after
- [ ] Deep links land on the right page, prefilled; suggestion routes match App.tsx (guard test green)
- [ ] Permission-filtered: unpermitted user sees the calm alternative, never a disabled button
- [ ] Full PO story: upload → missing supplier → create → auto return → welcome-back names the
      record → original extracted values intact → proposal resumes; zero re-upload, zero re-extract
- [ ] Detour survives a browser reload; cancel and stale (30 min) paths both behave
- [ ] Import preview with a missing reference offers a detour, not a dead error row

## Regression Checklist

- [ ] `/api/assistant/ask` and the four original suggestion chips work unchanged
- [ ] Invoice `extract-document` → confirm-draft flow untouched
- [ ] Command palette ⌘K, `?` dialog, `G`-navigation, j/k lists — no shortcut collisions (⌘J free)
- [ ] Help Center opens beside/over the panel without z-index fights
- [ ] Docked mode: no layout shift on any dense page (journals, stock counts); narrow-width drawer unaffected
- [ ] Dark mode: panel, cards, code blocks — all tokens, no hardcoded surprises
- [ ] `pytest erp/` (full suite), `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`,
      `python scripts/gates/gate03.py` — all green

## Micro-polish pass (apply where missing)

- [ ] Panel open/close on the motion token scale; reduced-motion = instant
- [ ] Focus order: trigger → composer → messages → back; focus returns on close
- [ ] `aria-live="polite"` on the streaming region; steps summarized, not spammed
- [ ] Empty states: first-run, no-search-match, archived-empty — each designed, warm, both languages
- [ ] Timestamps localized; Arabic plural forms correct in every count string
- [ ] Long unbroken strings (SKUs, URLs) wrap inside bubbles; tables scroll inline, not the panel

## Brand-feel checklist (judgment, not mechanical)

Run the `conductor-brand` checklist on: the panel shell, a streamed answer with steps, an
ActionCard, an ImportCard, and every empty state. The bar: "would Linear ship this?" — monochrome
chrome, colour only inside content and always paired with a word, one type voice, calm copy, no
chatbot theatrics.

## Sign-off block

Record in the PR description:
- **Built:** conversations + streaming + context envelope (Phase 1); global panel, threads,
  messages, attachments (Phase 2); tool catalog, agent loop, safe actions, page assistant, guided
  detours + workflow resume, file import (Phase 3).
- **Not touched:** audit models, tokens.css, money lib, existing contract signatures, other apps'
  migrations. No new npm dependencies. No free-text SQL anywhere.
- **Deviations from the original spec (deliberate):** no SQL generation (DECISIONS: tool-use only);
  share-conversations and bookmarks deferred (thin value vs. surface area — revisit on demand);
  charts inside answers deferred until a first real chart need appears; import missing-reference
  detour ("Import preview with a missing reference offers a detour, not a dead error row") does not
  apply — the three import targets (customers/suppliers/items) are FK-free at create time, so a bad
  row is a plain listed error/skip, never a detour (see `imports.py` module docstring).
- Update the `erp-status` skill anchor and `DECISIONS.md` (agent-loop bounds, action confirm
  discipline, import discipline).

---

## After This Session

```
All checklists passed?
→ Rename this file: append _done. The whole plan is now closed - never reopen _done files.
→ Merge feat/ai-workspace → main
→ Start a FRESH session for whatever comes next (one task = one session)
```
