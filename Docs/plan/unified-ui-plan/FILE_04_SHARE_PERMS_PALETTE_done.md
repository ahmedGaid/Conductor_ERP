# FILE_04 — Share (copy link), permission gating, ⌘K palette registration

**Model:** Sonnet · **Est:** 25 min · **MERGE CHECKPOINT after this file**

## Goal

- **مشاركة** works everywhere: copies the record's app URL, success toast. No backend.
- ⋯ items the user lacks permission for are ABSENT (not greyed).
- Every page's bar actions also appear in the ⌘K palette ("طباعة", "تصدير…") — keyboard-first.

## Before You Start — read these (mandatory)

- FILE_00 index (decisions 2, 4)
- `apps/web/src/app/PaletteActionsContext.tsx` + `app/CommandPalette.tsx` — how pages already
  register palette actions (the registry EXISTS; find the shape and reuse)
- How the frontend knows permissions: grep `permissions`/`modules` in `preferences/` and
  `identity` API types (`serialize_detail` ships `permissions` + `modules`). Find the existing
  hook/context the app uses for "can this user X" — REUSE it; if none exists client-side,
  gate by `modules` accessibility as the coarse filter and note the finer check as follow-up.
  **Do not invent a parallel permission system.**

## Tasks

1. **Share item** as a standard `DocMenuItem` factory (one helper, e.g. `shareMenuItem(t, toast)`):
   `navigator.clipboard.writeText(location.href)` → success toast. Clipboard can fail (http,
   permissions) → blame-free error toast, never silent. Term: **نسخ الرابط** vs **مشاركة** —
   pick ONE with the lexicon (Identity System §6) BEFORE the key ships; the menu label and the
   toast must use it consistently.
2. Wire the helper into every ⋯ published in FILE_02/03 (replace placeholders).
3. **Permission filter:** central helper `filterMenuItems(items, perms)`; each `DocMenuItem`
   gains optional `permission?: string`. Bar and palette both filter through it. Absent, silent.
4. **Palette:** on publish, `PageActionsContext` mirrors menu items + primary into the palette
   registry (and removes them on route change). ⌘K on an invoice → typing "طباعة" prints.
5. i18n keys; parity.

## Acceptance

- Copy-link works on detail + report pages, both locales; pasting the URL as the other logged-in
  role either opens the record or shows the existing permission-denied state.
- A restricted role sees NO share/export items it lacks (verify with a non-admin dev user).
- ⌘K lists the current page's actions; runs them; they vanish after navigating away.

## Gates

Parity + `npx tsc -b` + gate03. Brand check: toast copy is human, blame-free.
Commit → `_done` → `erp-status` → fresh session.

---
**Merge checkpoint:** header-bar program (01–04) merges to main here. Demo: sticky bar with
arrows on every page, unified actions, share, palette. Then start FILE_05 on a fresh branch.
