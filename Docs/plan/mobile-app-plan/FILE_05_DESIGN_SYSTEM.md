# SESSION 5 — Design System Primitives
# Files: apps/mobile/lib/presentation/widgets/common/** (new), apps/mobile/lib/core/icons/** (new),
#        i18n locales (mobile.* keys), test/goldens/** (new), apps/mobile/PARITY.md

**Objective:** the complete widget vocabulary every screen will be assembled from — built once,
token-driven, RTL-native, dark-mode-automatic, with designed empty/error/loading states as
first-class widgets, and a **golden-test harness** that pins every primitive pixel-for-pixel in
RTL + LTR × light + dark. After this session, no screen session ever styles from scratch, which
is how 15 screens end up feeling like one product — and no regression sneaks past unseen.

**Brand law (from `conductor-brand` — recall that skill when executing):** monochrome chrome;
colour only inside content and always paired with a word/icon; one type voice; own single-stroke
icons; settled motion from the token scale; human, blame-free copy.

---

## Before You Start

1. Recall the `conductor-brand` skill; open `Docs/Brand/` Directive → the in-app behaviour rules.
2. Recall `flutter-lessons` (issue 10 — directional layout only).
3. Open `apps/web/src/app/icons.tsx` → inventory the icon set: names, stroke width, viewBox.
4. Open 3 web components for voice-matching: a button, a list row, an empty state (find via the
   web pages) → note paddings, radii, type sizes actually used.
5. Open the generated `lib/core/theme/tokens.dart` → the only styling values you may use.
6. Decide the golden-test approach: plain `matchesGoldenFile` from `flutter_test` is enough — no
   new dependency unless a real need appears (then DECISIONS).

"Do not write anything yet."

---

## Task A — Foundations (`lib/presentation/widgets/common/`)

1. `AppText`: variants (`title`, `heading`, `body`, `label`, `caption`, `number`) mapping to the
   token type scale. `number` variant uses tabular figures
   (`fontFeatures: [FontFeature.tabularFigures()]`) — financial columns must align. Font family
   resolves Arabic vs Latin automatically (Plex Arabic handles Latin acceptably; verify against
   web's stack choice and mirror it).
2. `AppPressable` wrapper: 44×44 dp minimum touch target (pad, don't grow visuals), pressed
   state = token opacity/bg shift (no Material ripple colour outside tokens — set
   `splashFactory: NoSplash.splashFactory` if ripple fights the brand), `HapticFeedback.lightImpact`
   on destructive/confirm actions only — Telegram-calm, not buzzy.
3. Layout discipline: `EdgeInsetsDirectional`, `Alignment.centerStart/End`, `PositionedDirectional`
   only. **Grep-gate (session 19) will ban `EdgeInsets.only(left:|right:)`, `Alignment.centerLeft`,
   `Alignment.centerRight` in `lib/` — write accordingly from day one.**
4. Motion: `lib/core/theme/motion.dart` — the ONLY animation constants (`TokenMotion` durations/
   curves); a `reducedMotion(context)` helper reading `MediaQuery.disableAnimations` that every
   animation must consult. No spring/bounce curves anywhere.

## Task B — Components

Build, each with RTL + dark verified as you go:
- `AppButton` (primary/secondary/quiet/destructive), `AppIconButton`
- `AppInput`, `AppSearchField` (with clear affordance), `AppSelect` (opens an AppSheet)
- `AppCard`, `ListRow` (title/subtitle/meta/chevron — chevron flips in RTL automatically via a
  directional icon wrapper, NEVER a hardcoded arrow glyph — this was a real web bug, see memory),
  `SectionHeader`
- `AppSheet` (bottom sheet: `showModalBottomSheet` with token-timed transition; drag-to-dismiss;
  this is mobile's equivalent of web's peek panel), `AppDialog` (confirm destructive actions)
- `AppToast` (top, quiet, auto-dismiss; queue of one; success/undo variants — mirrors web's toast
  primitive semantics; own overlay, not `SnackBar` styling defaults), `OfflinePill` (the
  session-04 indicator: monochrome, word + icon)
- `StatusChip` — statuses use the SAME wording and colour pairings as web (find web's status
  rendering; colour always pairs with the word)

## Task C — Designed states (first-class, mandatory)

- `EmptyState` (icon + one human sentence + optional action — copy comes from the same i18n keys
  web uses for its empty states where they exist)
- `ErrorState` (blame-free sentence + retry button; never a raw message or code)
- `AppSkeleton` (list-row and card shapes; shimmer only if reduced-motion off, else static)

Every future screen MUST render one of these three for its empty/error/loading branches — bare
"No data" is a review-rejection.

## Task D — Icons (`lib/core/icons/`)

Port the web icon set to Flutter `CustomPainter` path widgets — same names, same geometry, same
stroke width, colour prop defaulting to the current token text colour. Directional icons
(back/forward/chevron) get an automatic RTL flip wrapper reading `Directionality.of(context)`.
Add a gallery dev screen rendering every icon + component in all states (this screen stays
forever — it is the living style guide and the brand-review surface).

## Task E — Golden harness (`test/goldens/`)

One parameterised helper: pump a widget inside the app theme at a fixed size, capture goldens for
the four combinations **RTL+light, RTL+dark, LTR+light, LTR+dark**. Every Task B/C component and
every icon gets a golden. `flutter test --update-goldens` regenerates deliberately; CI (session
19) fails on pixel drift. This is the mechanical half of the brand gate for mobile.

---

## Smoke Test

- [ ] Gallery screen: every component, Arabic RTL — chevrons/back arrows point correctly, text
      aligns start, layout mirrors
- [ ] Same gallery in English LTR — reads identically well
- [ ] Dark mode flip: every component correct in both schemes, no hardcoded colour survives
      (grep `Color(0x` in `apps/mobile/lib` → zero hits outside `tokens.dart`)
- [ ] Reduced motion ON (OS setting): sheet/toast/skeleton animate instantly/statically
- [ ] Touch targets: enable "Show layout bounds"/Accessibility Inspector → all interactive
      elements ≥ 44 dp
- [ ] Golden suite green: all primitives × 4 combinations; deliberately break one padding →
      golden fails → revert (harness proven)
- [ ] All copy through `t()`; parity checker green; `flutter analyze` + `flutter test` green
- [ ] PARITY.md rows for "design primitives" flipped to done

## Risks

- Icon port fidelity → side-by-side screenshot vs web at same optical size; brand checklist eye.
- Font rendering differences between golden CI environment and local → generate goldens on one
  canonical environment and document it (goldens are same-platform comparisons).
- Sheet gesture jank → keep v1 simple (tap-scrim dismiss + drag handle); no gesture library.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_06_NAVIGATION_SHELL.md
```
