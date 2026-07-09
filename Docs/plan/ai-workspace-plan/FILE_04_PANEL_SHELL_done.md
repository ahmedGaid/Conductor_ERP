# SESSION 4 — Global Panel Shell + Entry Point
# Files: apps/web/src/assistant/AssistantProvider.tsx (new), apps/web/src/assistant/AssistantPanel.tsx (new), apps/web/src/assistant/assistant-panel.css (new), apps/web/src/app/AppShell.tsx, apps/web/src/app/CommandBar.tsx, apps/web/src/app/ShortcutsDialog.tsx, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json

---

## Before You Start

1. Open `apps/web/src/app/AppShell.tsx` → read the full provider nesting (ToastProvider →
   ActionFeedback → Help → PaletteActions → Shortcuts) and where `HelpCenter` mounts (line ~98) —
   the panel mounts beside it.
2. Open `apps/web/src/help/HelpContext.tsx` + `HelpCenter.tsx` → this pair is the exact pattern to
   copy for provider + host (open state, Esc handling, focus, CSS).
3. Open `apps/web/src/app/CommandBar.tsx` → find where global buttons render (help, menu) — the AI
   button sits with them, identical treatment.
4. Open `apps/web/src/app/ShortcutsContext.tsx` → how the global `?` key is registered; mirror it.
5. Open `apps/web/src/pages/assistant/assistant.css` → existing assistant class vocabulary; extend
   the same naming (`assistant-…`).
6. Open `apps/web/src/styles/tokens.css` → note surface/border/shadow/z-index and motion tokens to
   use. No raw values.

"Do not write anything yet."

---

## Task A — AssistantProvider

Create `apps/web/src/assistant/AssistantProvider.tsx`, modeled on `HelpContext.tsx`:

```typescript
export type AssistantMode = "floating" | "docked" | "full";

interface AssistantState {
  open: boolean;
  mode: AssistantMode;          // persisted in localStorage "assistant.mode"
  conversationId: number | null; // persisted in localStorage "assistant.lastConversation"
  openPanel(): void; closePanel(): void; toggle(): void;
  setMode(m: AssistantMode): void;
  setConversationId(id: number | null): void;
  enabled: boolean;             // from assistantStatus(); false ⇒ every AI surface hidden
}
```

`enabled` loads once via `assistantStatus()` (it already exists in `api/assistant.ts`); while
unknown, render nothing — no flicker. Persisted mode + conversation restore instantly on mount:
reopening the app puts you exactly where you left off.

## Task B — Panel component

Create `AssistantPanel.tsx` + `assistant-panel.css`. Three renderings of ONE component (no
duplicate trees), switched by `mode`:

- **floating** — anchored `inline-end` bottom, ~420px wide, ~600px tall card; token shadow; opens
  with a settled slide from the end edge (motion tokens; honour `prefers-reduced-motion`).
- **docked** — full-height sidebar on the `inline-end` edge; `appshell__main` gets an
  `margin-inline-end` while docked (add a `data-assistant-docked` attribute on the shell root and
  handle it in `assistant-panel.css`).
- **full** — the existing `/assistant` route page becomes the fullscreen workspace (session 5 fills
  it); the panel's expand button navigates there and closes the overlay.

Panel chrome (monochrome, no colour): header with sparkle `NavIcon`, title `t("assistant.title")`,
mode toggle buttons (floating ⇄ docked, expand-to-full), close (Esc works everywhere — copy
HelpCenter's dialog/focus handling). Body for THIS session: mount the existing single-shot ask UI —
extract the form + answer rendering from `AssistantPage.tsx` into `AskView`-style shared components
so page and panel share one implementation. Panel must be functional today, not a placeholder.

## Task C — Entry points

1. `AppShell.tsx`: wrap children with `AssistantProvider` (inside ToastProvider, beside
   HelpProvider); mount `<AssistantPanel />` next to `<HelpCenter />` (line ~98).
2. `CommandBar.tsx`: add the sparkle button next to the existing global buttons — same size, same
   hover treatment, `aria-label={t("assistant.open")}`. Hidden entirely when `!enabled`.
3. Keyboard: register `⌘J` / `Ctrl+J` → `toggle()`, following the ShortcutsContext pattern (must
   not fire inside inputs — copy the existing guard).
4. `ShortcutsDialog.tsx`: find the `general` array (line ~36) and add
   `{ keys: ["⌘", "J"], label: t("shortcuts.assistant") }`.

## Task D — i18n

Add to BOTH `ar.json` and `en.json` under the existing `assistant.` namespace: `open`, `close`,
`dock`, `float`, `expand`, plus `shortcuts.assistant`. Arabic: use the canonical lexicon —
المساعد is already the product word; keep it (check existing `assistant.title` first and stay
consistent).

---

## Smoke Test

- [ ] Sparkle button visible on every page, identical position; ⌘J opens/closes
- [ ] Panel opens floating; toggle to docked shifts content; expand goes fullscreen `/assistant`
- [ ] Mode + open state survive a full page reload
- [ ] Esc closes; focus returns to the trigger; reduced-motion shows no slide
- [ ] RTL (Arabic): panel anchors to the correct end edge; LTR mirrors perfectly
- [ ] With the AI provider key removed (`enabled: false`) → no button, no shortcut, no panel
- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit` green; `python scripts/gates/gate03.py` green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_05_THREADS.md and continue
```
