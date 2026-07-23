# SESSION 12 — Wizard UI 1: Upload → Detect → Map
# Files: apps/web/src/pages/imports/ImportWizard.tsx, UploadStep.tsx, MappingStep.tsx, imports.css (new), apps/web/src/api/imports.ts (new), router + nav entry, i18n/locales/ar.json + en.json

> Recall `conductor-brand` + `erp-frontend` skills BEFORE building. RTL first.

---

## Before You Start

1. Open an existing multi-step page or the closest pattern (find one — grep `step` in
   `apps/web/src/pages`) + `assistant/ImportCard.tsx` if ai-workspace FILE_14 landed → reuse
   its mapping-table look; the wizard is the full-page big sibling, same visual language.
2. Open `apps/web/src/api/` (any file) → fetch wrapper pattern; `i18n` structure.
3. Open `styles/tokens.css` → spacing/motion tokens you'll use. No new hex.

"Do not write anything yet."

---

## Task A — Route + shell

`/imports/new` → `ImportWizard` with step rail (Upload → Map → Review → Import — the rail
shows all four; sessions 13–14 fill the last two). State from the batch object (server is the
source of truth; refresh-safe by batch id in the URL: `/imports/{id}`).

## Task B — UploadStep

Drag-drop + file picker (xlsx/csv; .xls rejected with the save-as-xlsx message). Designed
states: empty (what to drop, "your file as it is — no template needed" line from the brand
voice), uploading (progress), error (blame-free). On response: detection result —
high confidence → "This looks like sales invoices" (`imports.detect.looksLike` with entity
interpolation) + continue; low → candidate choice list (radio, confidence as words+icon, not
naked percentages). Profile hit → "Use saved mapping 'ABC Sales'?" chip.

## Task C — MappingStep

Table: file column | sample values (2) | mapped field (select from adapter field specs,
grouped required-first) | confidence indicator (word + icon; colour only beside the word).
Unmapped → "ignored" pill. Required-field gaps block Continue with a designed inline notice.
"Save as profile" (name input). Continue → POST mapping → analyze stats screen: the
spec-step-6 numbers as a calm stat list ("520 invoices · 35 new customers · 820 new items"),
then into Review (session 13).

Drag-drop mapping is NOT v1 — selects are faster and keyboard-friendly; note in the file as a
deliberate cut (Linear test: fewer, better interactions).

## Task D — i18n + nav

`imports.*` keys in BOTH locales (wizard, upload, detect, mapping, stats — Arabic plural forms
for counts). Nav entry per the app's nav pattern (monochrome icon from `src/app/icons.tsx` —
add one single-stroke import glyph there if missing).

---

## Smoke Test

- [ ] ar RTL: full flow reads right; step rail, table, pills all logical-CSS (flip to LTR — identical)
- [ ] Customer csv → detected, mapped, stats screen shows correct counts
- [ ] Ambiguous file → candidate chooser; .xls → designed error state
- [ ] Profile saved then auto-suggested on re-upload
- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit` + `python scripts/gates/gate03.py` green + brand-feel checklist pass

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_13_PREVIEW_FIX_UI.md in a FRESH session.
```
