# FILE_07 — Meta-column primitives (StatusRing, OwnerChip, PriorityBar, DueMarker)

**Model:** Opus · **Est:** 30 min

## Goal

The four at-a-glance cell components, hand-drawn in the app's own icon hand (single-stroke,
`currentColor`, 24-grid, tokens only), + the lifecycle-stage map that feeds the ring. Linear's
information density, Conductor's quiet. NO rollout yet (FILE_08).

## Before You Start — read these (mandatory)

- FILE_00 index (decisions 5–7, 9) — ring = lifecycle stage; chip = initials; priority only
  where worked; overdue markers on money docs
- `apps/web/src/app/icons.tsx` — the icon recipe to match (stroke width, caps, grid)
- `apps/web/src/styles/tokens.css` — status/danger/warn colour tokens that exist; NO new hex
- Status vocabularies per doc type: grep `ORDER_STATUSES` and each module's status unions in
  `api/*.ts` (sales, purchasing, accounting journals, CRM) — build the map from CODE, not memory
- `Docs/Brand/Conductor_ERP_Product_Design_Engineering_Directive.md` — colour-with-word rule

## Tasks

1. **`lib/lifecycle.ts`** — per doc type: ordered stage list → fraction (draft=first step,
   terminal=1.0). Cancelled/rejected are NOT on the line — they render as the status word +
   hollow ring (no fill), never a "progress". Export `lifecycleFraction(docType, status)`.
2. **`components/StatusRing.tsx`** — SVG circle, hairline track (`--color-border`-ish token),
   arc = fraction via stroke-dasharray. Colour: the SAME token the status word already uses on
   that page, and the ring NEVER appears without the status word beside it (prop-enforced:
   component renders ring+word together). Size fits table row height. `aria-hidden` on the
   ring; the word carries meaning.
3. **`components/OwnerChip.tsx`** — monochrome initials circle (first letters of display name,
   Arabic-aware — first grapheme of first two words), Tooltip = full name. `Bdi` inside. No
   photos (follow-up plan).
4. **`components/PriorityBar.tsx`** — 3 ascending bars, filled count = level, monochrome;
   ONLY the top level may use the danger token AND then the label word renders beside it
   (colour never alone). Tooltip = level word from the lexicon.
5. **`components/DueMarker.tsx`** — due-date cell: normal date; due-soon → warn token + word
   (e.g. يستحق قريبًا); overdue → danger token + word (متأخر) + days count (Latin digits,
   `.num`). Words: settle EXACT Arabic terms in Identity System §6 FIRST.
6. Motion: none, or one settled fade on mount — no draws/spins; reduced-motion safe.
7. i18n keys for all words; parity.

## Acceptance

- A scratch/story render (temporary route or an existing page corner, removed before commit)
  shows all four in AR + EN, light + dark, RTL + LTR — aligned to row height, tabular digits.
- Ring/word inseparability enforced by the component API (cannot render colour alone).
- gate14 (Latin digits) clean; zero new hex outside tokens.css.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist (esp. "colour means something", "one icon
hand"). Commit → `_done` → `erp-status` → fresh session.
