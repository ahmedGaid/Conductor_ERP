# SESSION 5 — Design System Primitives
# Files: apps/mobile/src/ui/** (new), apps/mobile/src/icons/** (new),
#        i18n locales (mobile.* keys), apps/mobile/PARITY.md

**Objective:** the complete component vocabulary every screen will be assembled from — built
once, token-driven, RTL-native, dark-mode-automatic, with designed empty/error/loading states as
first-class components. After this session, no screen session ever styles from scratch, which is
how 15 screens end up feeling like one product.

**Brand law (from `conductor-brand` — recall that skill when executing):** monochrome chrome;
colour only inside content and always paired with a word/icon; one type voice; own single-stroke
icons; settled motion from the token scale; human, blame-free copy.

---

## Before You Start

1. Recall the `conductor-brand` skill; open `Docs/Brand/` Directive → the in-app behaviour rules.
2. Open `apps/web/src/app/icons.tsx` → inventory the icon set: names, stroke width, viewBox.
3. Open 3 web components for voice-matching: a button, a list row, an empty state (find via the
   web pages) → note paddings, radii, type sizes actually used.
4. Open `packages/core/tokens.ts` → the only styling values you may use.

"Do not write anything yet."

---

## Task A — Foundations (`src/ui/`)

1. `Text.tsx`: variants (`title`, `heading`, `body`, `label`, `caption`, `number`) mapping to the
   token type scale. `number` variant uses tabular figures (`fontVariant: ['tabular-nums']`) —
   financial columns must align. Font family resolves Arabic vs Latin automatically (Plex Arabic
   handles Latin acceptably; verify against web's stack choice and mirror it).
2. `Pressable.tsx` wrapper: 44×44 dp minimum touch target (pad, don't grow visuals), pressed
   state = token opacity/bg shift (no ripple colour outside tokens), `expo-haptics` light tap on
   destructive/confirm actions only — Telegram-calm, not buzzy.
3. Layout helpers: `Row`/`Stack` with logical props only (`gapStart`, `padEnd`…) mapping to
   `marginStart/paddingEnd` RN logical properties. **Grep-gate (session 19) will ban
   `marginLeft|Right|paddingLeft|Right` in `src/` — write accordingly from day one.**
4. Motion: `src/ui/motion.ts` — the ONLY animation constants (durations/easings from
   `tokens.motion`); a `useReducedMotion()` hook (RN `AccessibilityInfo`) every animation must
   consult. No spring/bounce anywhere.

## Task B — Components

Build, each with RTL + dark verified as you go:
- `Button` (primary/secondary/quiet/destructive), `IconButton`
- `Input`, `SearchField` (with clear affordance), `Select` (opens a Sheet)
- `Card`, `ListRow` (title/subtitle/meta/chevron — chevron flips in RTL automatically via logical
  layout, NEVER a hardcoded arrow glyph — this was a real web bug, see memory), `SectionHeader`
- `Sheet` (bottom sheet: RN `Modal` + token-timed translate; drag-to-dismiss; this is mobile's
  equivalent of web's peek panel), `Dialog` (confirm destructive actions)
- `Toast` (top, quiet, auto-dismiss; queue of one; success/undo variants — mirrors web's toast
  primitive semantics), `OfflinePill` (the session-04 indicator: monochrome, word + icon)
- `StatusChip` — statuses use the SAME wording and colour pairings as web (find web's status
  rendering; colour always pairs with the word)

## Task C — Designed states (first-class, mandatory)

- `EmptyState` (icon + one human sentence + optional action — copy comes from the same i18n keys
  web uses for its empty states where they exist)
- `ErrorState` (blame-free sentence + retry button; never a raw message or code)
- `Skeleton` (list-row and card shapes; shimmer only if reduced-motion off, else static)

Every future screen MUST render one of these three for its empty/error/loading branches — bare
"No data" is a review-rejection.

## Task D — Icons (`src/icons/`)

Port the web icon set to `react-native-svg` components — same names, same viewBox, same stroke
width, `currentColor` → prop-driven token colour. Directional icons (back/forward/chevron) get an
automatic RTL flip wrapper. Add a gallery dev screen rendering every icon + component in all
states (this screen stays forever — it is the living style guide and the brand-review surface).

---

## Smoke Test

- [ ] Gallery screen: every component, Arabic RTL — chevrons/back arrows point correctly, text
      aligns start, layout mirrors
- [ ] Same gallery in English LTR — reads identically well
- [ ] Dark mode flip: every component correct in both schemes, no hardcoded colour survives
      (grep `#[0-9a-fA-F]{3,8}` in `apps/mobile/src` → zero hits outside generated tokens import)
- [ ] Reduced motion ON (OS setting): sheet/toast/skeleton animate instantly/statically
- [ ] Touch targets: enable "Show layout bounds"/Accessibility Inspector → all interactive
      elements ≥ 44 dp
- [ ] All copy through `t()`; parity checker green; `npx tsc --noEmit` green
- [ ] PARITY.md rows for "design primitives" flipped to done

## Risks

- Icon port fidelity → side-by-side screenshot vs web at same optical size; brand checklist eye.
- Sheet gesture jank → keep v1 simple (tap-scrim dismiss + drag handle); no gesture library.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_06_NAVIGATION_SHELL.md
```
