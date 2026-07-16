# SESSION 8 — ⌘K as an Action Surface
# Files: apps/web/src (⌘K module + per-module action registry), i18n locales

Twenty reference: the command menu is not navigation — it hosts record ACTIONS, search, and the
AI entry, aware of the current context (`context-store`). One keystroke = one mental home for
everything. Pure ARP energy: operate, not just display.

---

## Before You Start

1. **Overlap audit (mandatory):** linear-polish shipped a "⌘K bridge". Open the existing ⌘K
   implementation (`apps/web/src` — grep for the command palette component) → catalog what it
   already does (nav? search? actions?). This session EXTENDS it.
2. Open one page with a primary action (sales order detail) → how actions are invoked today
   (the unified header bar's primary + ⋯ menu from unified-ui) — ⌘K reuses THOSE handlers,
   never duplicates mutation logic.
3. Open the assistant entry surface → how a conversation opens with context today.

"Do not write anything yet."

---

## Task A — Action registry

Per-module registry: `{id, i18n label key, icon (own set), scope: global|page|record, roles?,
run(ctx)}`. Populated from the SAME handlers the header bar uses. Permission-filtered against
the user's roles client-side AND enforced (as today) server-side.

## Task B — Context-aware sections

⌘K opens with sections, in order: **Actions on this page/record** (e.g. on an invoice:
تسجيل الدفع / Export / Share) → **Create** (global creates) → **Go to** (nav) → **Recents**
(last visited records; reuse whatever recents/prefetch state exists) → **اسأل المساعد / Ask the
assistant** (opens the assistant pre-primed with the current page/record context — Twenty's
"preprompt" pattern; read-only context injection, no auto-action).

## Task C — Craft

Keyboard-only path complete (arrows/enter/esc); settled motion tokens; empty query shows
sections, typing filters across them with the section headers kept; no new icons, no color in
the chrome. Both languages; ar first.

---

## Smoke Test

- [ ] On an invoice: ⌘K → its record actions appear and RUN (same result as header-bar action)
- [ ] Role without permission → action absent from ⌘K (and server still rejects direct calls)
- [ ] "Ask the assistant" opens assistant with this record's context visible
- [ ] Keyboard-only round trip works; RTL layout correct; reduced-motion honoured
- [ ] parity + tsc + gate03 green; brand-feel checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_09_APPROVAL_NODE.md in a FRESH session.
```
