# SESSION 16 — UX States Batch: Empty-State Taxonomy + Skeletons + Cheatsheet
# Files: apps/web/src (shared state components + list-page audit + `?` overlay), i18n locales

Twenty reference: empty states have CAUSES (distinct components for: no records at all / none
match the filter / read-only / not shared), skeletons load per PANE (nav, panel, content
separately), and `?`-style discoverability makes power users. All three are cheap, systematic
calm.

---

## Before You Start

1. Open the existing designed empty-state component(s) (brand rule: every state designed — so
   one exists; find it) → this session adds the TAXONOMY on top, not a new look.
2. Grep list pages for their empty handling → build the audit table (page × which cause it can
   distinguish today).
3. Open the keyboard shortcuts registry (linear-polish keyboard work + FILE_08 registry) → the
   cheatsheet renders FROM it — never a hand-maintained list.
4. Open current loading treatments (spinners? existing skeletons?) → inventory before changing.

"Do not write anything yet."

---

## Task A — Empty-state taxonomy

One shared component, three variants, each with its own copy + action:
- **no-data-yet** — "لا توجد فواتير بعد" + primary create action (+ optional help-journey link
  from FILE_15)
- **no-match** — "لا نتائج لهذه التصفية" + "مسح التصفية / Clear filters" action (NEVER shows a
  create CTA — creating because a filter is empty is how duplicate data happens)
- **no-permission** — calm, blame-free, names the role needed, no dead-end ("اطلب صلاحية…")

Audit pass: every list page uses the RIGHT variant (filtered-empty ≠ truly-empty is the bug
class this kills).

## Task B — Skeletons per pane

Shared skeleton primitives (bar/block/row) on tokens; apply so the app frame paints instantly
and panes fill independently (nav, page header, table body, side panel). Settled motion only —
a quiet shimmer at most; honour reduced-motion (static blocks). Replace any remaining spinners
on the main surfaces.

## Task C — `?` cheatsheet overlay

`?` (when not typing in an input) opens a shortcuts overlay grouped by area, rendered from the
registry, both languages, dismiss on esc/click-out. One line in the help page (FILE_15) points
to it.

---

## Smoke Test

- [ ] Filter a populated list to zero → no-match variant with clear-filters (no create CTA)
- [ ] Truly empty list → no-data variant with create action
- [ ] Low-permission user on a restricted page → no-permission variant, blame-free
- [ ] Throttled network: frame + skeletons paint first, panes fill independently;
      reduced-motion shows static placeholders
- [ ] `?` shows the cheatsheet in ar and en; esc closes
- [ ] parity + tsc + gate03 green; brand-feel checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_17_LIST_UX.md in a FRESH session.
```
