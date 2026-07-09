# SESSION 5 — Threads: History, Search, Rename, Pin, Archive, Delete
# Files: apps/web/src/api/assistant.ts, apps/web/src/assistant/ThreadList.tsx (new), apps/web/src/assistant/AssistantPanel.tsx, apps/web/src/pages/assistant/AssistantPage.tsx, apps/web/src/assistant/assistant-panel.css, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json

---

## Before You Start

1. Open `apps/web/src/api/assistant.ts` → confirm session-1 endpoints aren't wrapped yet.
2. Open `apps/web/src/lib/useAsync.ts` (find it via its import in any list page) → the load/cache
   pattern every list uses; ThreadList uses the same, with cache key `"assistant:conversations"`.
3. Open `apps/web/src/pages/crm/` (any list page) → house style for list rows, hover actions,
   inline rename, and `useListKeyboardNav` (j/k/Enter).
4. Open `apps/web/src/components/EmptyState.tsx` and `ListSkeleton.tsx` → the designed states to
   reuse.
5. Open `apps/web/src/assistant/AssistantProvider.tsx` → `conversationId` / `setConversationId`
   from session 4.

"Do not write anything yet."

---

## Task A — API wrappers

In `api/assistant.ts` add typed wrappers over session 1's endpoints:

```typescript
export interface ConversationSummary {
  id: number; title: string; pinned: boolean; archived: boolean;
  updated_at: string; preview: string;
}
export function listConversations(q?: string, archived?: boolean): Promise<ConversationSummary[]>
export function createConversation(): Promise<ConversationSummary>
export function getConversation(id: number): Promise<{ conversation: ConversationSummary; messages: ChatMessage[] }>
export function updateConversation(id: number, patch: Partial<Pick<ConversationSummary, "title" | "pinned" | "archived">>): Promise<ConversationSummary>
export function deleteConversation(id: number): Promise<void>
```

`ChatMessage` = `{ id, role: "user" | "assistant", content, meta, created_at }`. All via `apiFetch`.

## Task B — ThreadList component

Create `ThreadList.tsx`: search input (debounced 250ms, `dir="auto"`), then **pinned** group, then
the rest by `updated_at`, archived behind a quiet toggle at the bottom. Each row: title (or
`t("assistant.untitled")`), relative time, preview line; hover/focus reveals a compact action row —
rename (inline input, Enter commits, Esc cancels), pin/unpin, archive, delete. Delete asks once via
the app's existing confirm treatment (find how other destructive actions confirm — match it, don't
invent a new dialog). Optimistic updates + toast on failure, same pattern as other lists.

Selecting a row → `setConversationId(id)`. "New conversation" button on top: creates via
`createConversation()` and selects it. j/k/Enter keyboard nav via `useListKeyboardNav`.

Designed states: `ListSkeleton` while loading; `EmptyState` with a warm first-run line
(`assistant.threads.empty` — "Your conversations will live here", proper Arabic equivalent);
search-no-match state reuses `filter.noMatch` keys.

## Task C — Mount in both surfaces

- **Fullscreen** (`AssistantPage.tsx`): becomes a two-column workspace — ThreadList as an
  `inline-start` rail (~280px), conversation view fills the rest. Keep the existing ask form as the
  conversation view for now (session 6 replaces it). Column split uses logical properties + grid.
- **Floating/docked panel**: no room for two columns — a history button in the panel header flips
  the body to ThreadList; picking a thread flips back. One component, two placements.

Opening a conversation loads messages via `getConversation` and renders them read-only above the
composer (plain rendering this session; markdown arrives in session 6). Send routes through the
session-2 `chatStream` with `conversation_id` — from this session on, panel messages persist.

## Task D — i18n

Both locales: `assistant.threads.*` — `title`, `new`, `search`, `empty`, `emptyHint`, `rename`,
`pin`, `unpin`, `archive`, `unarchive`, `archived`, `delete`, `deleteConfirm`, `untitled`.

---

## Smoke Test

- [ ] New conversation → send message → appears in list with auto-title from first message
- [ ] Reload app → panel restores the same conversation instantly (localStorage id + fetch)
- [ ] Search filters by content, not just title; no-match state is designed
- [ ] Rename inline; pin floats to top; archive hides from default list; delete removes after confirm
- [ ] Same list state visible in panel and fullscreen — one source of truth
- [ ] RTL: rail sits on the correct side; row actions align to the logical end
- [ ] i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_06_MESSAGES.md and continue
```
