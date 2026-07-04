# SESSION 6 — Knowledge-Base Management Page
# Files: apps/web/src/api/assistant.ts, apps/web/src/pages/assistant/KnowledgePage.tsx (new), page css, router/nav files, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json

---

## Before You Start

1. Open `apps/web/src/api/assistant.ts` → read the fetch helper pattern (envelope unwrapping,
   how the attachments upload posts FormData) — reuse both patterns.
2. Find the router + navigation registration: open the file that declares the `/assistant`
   route (search for `"assistant"` under `apps/web/src/app/`) → note how a page + nav entry +
   permission guard are registered, and how existing pages gate by role.
3. Open one existing list-style settings/admin page (whatever the nav shows — e.g. the users
   or administration page) → copy its layout skeleton, table/card idiom, and its designed
   empty/error/loading states.
4. Open `apps/web/src/pages/assistant/AssistantPage.tsx` → note the css import convention.
5. Recall rules: `conductor-brand` + `erp-frontend` skills — tokens only, logical CSS only,
   ar/en parity, monochrome chrome, designed states, settled motion.

Do not write anything yet.

---

## Task A — API functions in `api/assistant.ts`

Following the file's existing helper style, add:

```ts
export interface KnowledgeDoc {
  id: number;
  title: string;
  filename: string;
  status: "processing" | "ready" | "failed";
  error_text: string;
  chunk_count: number;
  size: number;
  updated_at: string;
}

export function listKnowledge(): Promise<KnowledgeDoc[]> { /* GET /api/assistant/knowledge */ }
export function uploadKnowledge(file: File, title: string): Promise<KnowledgeDoc> {
  /* POST FormData {file, title} — copy the attachments upload idiom */
}
export function deleteKnowledge(id: number): Promise<void> { /* DELETE /api/assistant/knowledge/<id> */ }
```

## Task B — `KnowledgePage.tsx`

New page, skeleton copied from the admin/list page you read:

- Header: title `t("knowledge.title")` + short description `t("knowledge.subtitle")`.
- Upload affordance: a file input (accept: pdf, images, txt, md, csv, xlsx) + optional title
  field; on pick → optimistic "processing" row → replace with server row. Failures use the
  existing toast primitive (blame-free copy).
- List: one row per document — title, filename, size, status as a **word chip** (colour always
  pairs with the word: processing/ready/failed), chunk count, updated date, delete action with
  the app's existing confirm idiom.
- A "failed" row shows its `error_text` inline under the row (calm, not red-screaming; token
  colours only).
- Designed states: empty state (what the knowledge base is + what uploading does for the
  assistant — this is the pitch surface, write it well in both languages), loading skeleton,
  error state with retry.
- Route + nav entry behind the SAME role gate the backend uses (read how other role-gated nav
  entries do it); users without the role never see the page.

## Task C — i18n keys (BOTH files, build-blocking)

Add under a `knowledge` namespace in `en.json` and `ar.json` — every key in both. Arabic first,
native (not translationese); one canonical word per concept — knowledge base = **قاعدة المعرفة**
(add it to Identity System §6 if it is not there yet — open `Docs/Brand/` and check):

```
knowledge.title            Knowledge base            قاعدة المعرفة
knowledge.subtitle         Documents the assistant can search and quote.
knowledge.upload           Upload document           رفع مستند
knowledge.docTitle         Title                     العنوان
knowledge.status.processing / ready / failed         (human words, blame-free)
knowledge.chunks           Sections
knowledge.empty.title / empty.body                   (designed empty state)
knowledge.delete / delete.confirm
knowledge.uploadFailed                               (blame-free)
```

(Exact English/Arabic copy: write it during the session under `conductor-brand` rules; the
table above is the key list, not final copy.)

## Task D — Styles

In the page css (new file next to the page, following `assistant.css` conventions): tokens
only, logical properties only, status chip = monochrome text + subtle token background —
colour only where the app already uses it for status words.

---

## Smoke Test

- [ ] `node scripts/check-i18n-parity.mjs` green; `npx tsc --noEmit` green
- [ ] `python scripts/gates/gate03.py` green
- [ ] As admin-role user: page visible in nav; upload a .txt → row appears, reaches "ready"
- [ ] Upload something unreadable → row shows "failed" + calm error text
- [ ] Delete works with confirm; empty state shows after deleting all
- [ ] As plain user: nav entry absent; direct route blocked
- [ ] Arabic UI: RTL layout correct, all strings Arabic, chips read naturally
- [ ] Run the `conductor-brand` brand-feel checklist on this page

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_06_KNOWLEDGE_UI_done.md
→ Type /compact in Claude Code
→ Open FILE_07_DOC_CITATIONS_UI.md and continue
```
