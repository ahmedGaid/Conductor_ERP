# SESSION 9 — Number Typography (Arabic craft)
# Files: apps/web/src/styles/ (one utility class file), lib/money.ts READ-ONLY check, table/money cells across pages, scripts/gates/ (extend gate03 or sibling), Docs/Brand (policy line)

---

## Before You Start

1. Open `lib/money.ts` → what locale/numbering it formats with today (Latin digits
   `1,234.56` vs Arabic-Indic `١٬٢٣٤٫٥٦`?). Open a money-heavy screen in ar → screenshot the
   current state.
2. Decide THE digits policy with the user's brand: recommendation = **Latin digits for all
   numerals in both locales** (Egyptian business convention: invoices, banks, ETA e-invoicing
   all use Latin digits; mixing hurts scanning). ONE policy, documented, enforced.
   → **Confirm this with the user before implementing if the current behaviour differs.**
3. Grep for existing table cell / money cell classes → where amounts render.
4. Open `Docs/Brand/` Identity System → where the policy line belongs.

Do not write anything yet.

---

## Task A — Tabular figures utility

One utility class (tokens file territory — css next to existing utilities, NOT tokens.css):

```css
.num {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}
```

(Verify IBM Plex Sans Arabic + Inter actually carry `tnum` — inspect in devtools; if a font
lacks it, document the fallback in the css comment.)

Apply `.num` to: money cells, quantity columns, totals rows, dashboard KPIs, the trial-balance
and report tables. Money stays formatted by `lib/money.ts` only — this session touches
PRESENTATION classes, never formatting logic.

## Task B — RTL money alignment

Audit every amounts column in ar: amounts right-aligned via `text-align: end` in LTR must
still align digits correctly in RTL (numbers are LTR runs inside RTL text). Fix with logical
properties + `unicode-bidi`/`direction: ltr` on the NUMBER SPAN only where a mixed row breaks
(e.g. negative sign position). Negative amounts: sign must render on the correct side in ar —
check `lib/money.ts` output in RTL context and wrap, don't reformat.

## Task C — Enforce

Extend the mechanical gate (gate03 or a sibling script in `scripts/gates/` — read how gate03
scans first): flag raw `font-variant-numeric` outside the utility + flag money-cell markup
missing `.num` if feasible; at minimum, add the digits-policy line to `Docs/Brand/` Identity
System and the check to the brand-feel checklist.

---

## Smoke Test

- [ ] Columns of amounts align digit-for-digit (screenshot before/after, ar + en)
- [ ] Negative amounts render correctly in RTL
- [ ] Dashboard KPIs, reports, trial balance all tabular
- [ ] Policy line lives in Docs/Brand; gate/checklist updated
- [ ] Gates green; visual pass on the 3 densest screens in ar

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_09_NUMBER_TYPOGRAPHY_done.md
→ /compact → FILE_10_PDF_POLISH.md
```
