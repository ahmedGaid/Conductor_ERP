# SESSION 10 — Arabic PDF / Print Craft Pass
# Files: the invoice/document PDF generation path (locate first), its templates/styles

---

## Before You Start

1. Locate PDF generation: grep `pdf` under `erp/` → find how invoices/documents render
   (library? HTML→print css?). Read the full path before judging anything.
2. Generate the CURRENT outputs: one Arabic invoice, one English invoice, a report export.
   Keep them as the "before" set.
3. Open `Docs/Brand/` Visual Identity System → the document/off-app surface rules (logo
   placement, type scale, spacing) — the PDF must obey the SAME identity as the app.
4. Recall `conductor-brand`: this is a judgment session — the checklist drives it, not a
   feature list.

Do not write anything yet.

---

## Task A — Audit against the checklist

Score the "before" set: Arabic type quality (correct font embedding — IBM Plex Sans Arabic,
no fallback tofu/naskh substitute), RTL layout integrity (labels/amounts columns, table
direction), digits policy (must match session 09's decision), money formatting, logo
(monochrome, correct clear-space), spacing rhythm vs the app's scale, footer/legal line, ETA
e-invoice required fields untouched. Write the defect list FIRST, as checkboxes, into this
session's commit description.

## Task B — Fix

Work the defect list. Rules: template/style changes only — never touch invoice DATA logic or
ETA compliance fields; fonts embedded/subset (customer-hosted, no CDN); both paper directions
verified (ar default, en identical grid mirrored).

## Task C — Regression pair

Save the "after" pair next to the "before" in `Docs/Brand/` (or wherever document samples
live — check) so future sessions have a visual baseline.

---

## Smoke Test

- [ ] Arabic invoice: correct shaping/ligatures, no fallback font anywhere (zoom 400% check)
- [ ] Tables: amounts aligned, digits per policy, totals row emphasized by weight not colour
- [ ] Logo + clear-space per Identity System; monochrome held
- [ ] English version = same grid, no drift
- [ ] ETA fields byte-identical where compliance requires (diff the generated XML/JSON if any)
- [ ] Before/after pair stored; defect list all ticked

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_10_PDF_POLISH_done.md
→ ARABIC CRAFT TIER COMPLETE — merge checkpoint.
→ /compact → FILE_11_AMBIENT_DIGESTS.md (fresh session, /model sonnet)
```
