# SESSION 7 — Document Citations in Chat
# Files: apps/web/src/assistant/MessageList.tsx, apps/web/src/assistant/assistant-panel.css, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json

---

## Before You Start

1. Open `apps/web/src/assistant/MessageList.tsx` → find where citation chips render (search
   for `citations`) → read the chip component/markup and what it does per citation `type`
   today (record types deep-link to their pages).
2. Open `apps/web/src/app/icons.tsx` → check whether a document/file icon already exists in
   the single-stroke set (chat attachments likely added one — REUSE it; only draw a new one in
   the same hand if truly absent).
3. Open `apps/web/src/assistant/assistant-panel.css` → find the existing citation-chip styles.

Do not write anything yet.

---

## Task A — Document-type citation chip

In the citation rendering you found, branch on `citation.type === "document"`:

- Chip shows the document icon + the document title (`citation.value`).
- A small prefix label distinguishes provenance: `t("assistant.citation.fromDocs")` —
  EN "From company documents", AR **"من مستندات الشركة"** (must match the prompt wording from
  backend session 05 — one canonical phrase).
- Not a dead chip: clicking navigates to the knowledge page (`/…/knowledge` route from
  session 06) — permission-aware: if the user lacks the knowledge-management role, the chip
  renders as a plain non-link chip (no dead link, no 403 trip).
- ERP-record citations keep rendering exactly as before — additive branch only.

## Task B — Styles

Extend the existing citation-chip css with a `document` variant: same chip anatomy, monochrome
(no new colour role), icon at `inline-start`, logical properties only.

## Task C — i18n

`assistant.citation.fromDocs` in BOTH `en.json` and `ar.json`.

---

## Smoke Test

- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit` + `python scripts/gates/gate03.py` all green
- [ ] Ask a policy question with a seeded doc → answer shows a document chip with icon +
      title + "من مستندات الشركة" label
- [ ] Admin user clicks the chip → lands on the knowledge page; plain user sees a non-link chip
- [ ] Ask a live-data question → record citations unchanged (regression)
- [ ] RTL: icon sits at inline-start, label reads naturally in Arabic
- [ ] Mixed answer (data + docs) shows both chip kinds side by side without layout break

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_07_DOC_CITATIONS_UI_done.md
→ RAG slice complete — natural merge checkpoint.
→ Type /compact in Claude Code
→ Open FILE_08_CONTEXT_ENVELOPE_PLUS.md and continue (fresh session)
```
