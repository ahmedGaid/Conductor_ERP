# SESSION 6 — Message Experience: Markdown, Streaming, Actions
# Files: apps/web/src/assistant/Markdown.tsx (new), apps/web/src/assistant/MessageList.tsx (new), apps/web/src/assistant/Composer.tsx (new), apps/web/src/assistant/AssistantPanel.tsx, apps/web/src/pages/assistant/AssistantPage.tsx, apps/web/src/assistant/assistant-panel.css, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json

---

## Before You Start

1. Open `apps/web/src/assistant/` session-5 output → ThreadList wiring, `getConversation`,
   `chatStream` usage.
2. Open `apps/web/src/pages/assistant/AssistantPage.tsx` → the `CitationLink` component — it moves
   into the shared message renderer.
3. Open `apps/web/src/components/Bdi.tsx` → bidi wrapper for mixed Arabic/Latin runs.
4. Open `apps/web/src/styles/tokens.css` → type scale + `latin` class usage for code.
5. Check `DECISIONS.md` for the no-new-deps rule — the markdown renderer below is written in-house;
   **do not** add `react-markdown`/`marked`.

"Do not write anything yet."

---

## Task A — Markdown-lite renderer (in-house, ~150 lines)

Create `Markdown.tsx`: a pure function of `text: string` → React nodes. Scope is exactly what an
AI answer needs — nothing more:

- paragraphs (blank-line separated), `**bold**`, `*italic*`, `` `inline code` ``
- fenced code blocks ```` ``` ```` → `<pre class="assistant-code latin" dir="ltr">` with a copy
  button (reuse the app's copy-to-clipboard + toast pattern if one exists — search for
  `clipboard` first)
- `- ` / `1. ` lists (nesting one level), `### ` headings (map to `<h4>` inside messages)
- GFM tables (`| a | b |` + separator row) → the existing table classes (`acct-table` vocabulary
  or a new `assistant-table` extending the same tokens)
- links: internal paths (`/sales/orders/42`) → `<Link>`; external → `<a rel="noopener" target="_blank">`

Escape HTML first; render text runs through `<Bdi>`; everything `dir="auto"`. No dangerouslySetInnerHTML.
Unit-test by eye with a fixture message (there is no JS test runner — put a `/assistant` dev
fixture behind `import.meta.env.DEV` or verify manually with a prompt that returns all constructs).

## Task B — MessageList + streaming bubble

Create `MessageList.tsx`: renders `ChatMessage[]` + the in-flight stream. User messages: quiet
end-aligned block (logical `inline-end`). Assistant messages: `Markdown` body + citations row
(move `CitationLink` here from AssistantPage; extend the icon map as tool types grow) + a hover
action row: **copy** (raw text), **regenerate** (last assistant message only), **edit prompt**
(on the preceding user message — loads it into the composer, focus, caret at end).

Streaming: while `chatStream` events arrive, append `token` text into a live bubble re-rendered
through `Markdown` (cheap at chat sizes), with a subtle caret token from the motion scale. A
**stop** button (`assistant.stop`) calls `AbortController.abort()` — the partial answer stays, per
session 2's server behaviour. On `error` event: designed inline error row with a **retry** button
(re-sends the same user message), blame-free copy.

Auto-scroll: pin to bottom only when the user is already at the bottom; new-content affordance
otherwise (small "↓ new reply" chip, `assistant.jumpNew`).

Suggested follow-ups: after `done`, if the answer's `meta` carries `followups` (backend: extend the
ask pipeline to also return up to 3 short follow-up questions in the final JSON — one extra field,
same completion), render them as chips using the existing `assistant-suggest__chip` class; clicking
sends.

## Task C — Composer

Create `Composer.tsx`: textarea `dir="auto"`, Enter sends / Shift+Enter newline (keep the exact
comment + behaviour from AssistantPage), grows to 6 rows max, disabled while streaming (stop button
replaces send). Placeholder = existing `assistant.placeholder`. This component is where session 7
adds attachments — leave a slot (`startSlot` prop) in the layout now.

## Task D — Replace the old rendering

`AssistantPage.tsx` (fullscreen) and `AssistantPanel.tsx` body both become: `MessageList` +
`Composer` (+ ThreadList per session 5). Delete the old one-shot answer card and its CSS once both
surfaces render through MessageList. First-run empty state: sparkle icon, one warm line, and the
four existing suggestion chips (`assistant.suggestions.s1–s4`) — keep them, they're good.

## Task E — i18n

Both locales: `assistant.copy`, `assistant.copied`, `assistant.stop`, `assistant.retry`,
`assistant.regenerate`, `assistant.editPrompt`, `assistant.jumpNew`, `assistant.errorLine`.

---

## Smoke Test

- [ ] Answer with code block, table, list, bold, link renders correctly in ar (RTL) and en
- [ ] Code blocks stay LTR/latin inside an RTL message; copy button works with toast
- [ ] Tokens stream visibly; stop keeps partial text; retry after a forced error works
- [ ] Edit prompt refills composer; regenerate replaces the last answer
- [ ] Follow-up chips appear and send on click
- [ ] Internal citation/link click navigates and closes the floating panel
- [ ] Scroll stays put when reading history while a reply streams
- [ ] i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_07_ATTACHMENTS.md and continue
```
