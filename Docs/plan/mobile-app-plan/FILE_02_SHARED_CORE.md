# SESSION 2 — Brand Bridge & Dart Core
# Files: scripts/generate-mobile-tokens.mjs (new, repo root), scripts/sync-mobile-i18n.mjs (new),
#        apps/web/scripts/check-i18n-parity.mjs, apps/mobile/lib/core/{theme,i18n,money}/** (new)

**Objective:** build the bridge between web truth and the Flutter app: design tokens generated
from `tokens.css`, the shared `ar.json`/`en.json` strings synced with a drift check, a
behaviour-identical `money` port verified against web-generated fixtures, and the token-built
theme. After this session, mobile literally cannot have its own colours, strings, or money math.

**Why generators, not copies:** a copied file diverges silently. A generated/synced file with a
`--check` mode makes web mechanically authoritative — change a colour or string on web, run the
script, mobile follows; CI fails on drift.

---

## Before You Start

1. Open `apps/web/src/styles/tokens.css` → read ALL custom properties; note naming groups
   (`--color-*`, spacing, radius, motion durations/easings, type scale) and the dark-mode
   selector the file actually uses.
2. Open `apps/web/src/lib/money.ts` → read fully; note every exported function, rounding rule,
   and locale behaviour (Arabic-Indic vs Latin digits — copy web's exact choice).
3. Open `apps/web/src/i18n/` → note how locales load, how keys are namespaced, and the EXACT
   interpolation syntax of the web `t()` helper.
4. Open `apps/web/scripts/check-i18n-parity.mjs` → understand how it finds used keys.
5. Recall `flutter-lessons` (money rule = issue 8).

"Do not write anything yet."

---

## Task A — Token generator

Create `scripts/generate-mobile-tokens.mjs` (repo root, plain Node, no deps):

1. Parse `apps/web/src/styles/tokens.css` with a regex over `--name: value;` declarations,
   capturing both the light (`:root`) and dark blocks.
2. Emit `apps/mobile/lib/core/theme/tokens.dart`:

```dart
// GENERATED from apps/web/src/styles/tokens.css — DO NOT EDIT.
// Run: node scripts/generate-mobile-tokens.mjs
abstract final class TokensLight {
  static const Color bg = Color(0xFF...);   // every --color-*
  ...
}
abstract final class TokensDark { /* same fields, dark values */ }
abstract final class TokenSpace { /* spacing scale, doubles in dp */ }
abstract final class TokenRadius { /* radii */ }
abstract final class TokenMotion { /* Durations + Curves from the token easings */ }
abstract final class TokenType { /* font sizes / line heights as doubles */ }
```

3. Convert `px`/`rem` to plain doubles (dp); hex `#RRGGBB` → `Color(0xFFRRGGBB)` (handle alpha
   forms if tokens.css has them). Fail the script loudly if light/dark key sets differ.
4. Add a `--check` mode (regenerate to temp, diff against committed file, exit 1 on drift) and
   wire it into `scripts/gates/gate03.py`'s checklist if that gate has an extension point — else
   note it for the session-19 CI wiring.

## Task B — Shared i18n

1. Create `scripts/sync-mobile-i18n.mjs` (plain Node): copy `apps/web/src/i18n/locales/ar.json` +
   `en.json` → `apps/mobile/assets/i18n/`, byte-identical, with the same `--check` drift mode as
   Task A. Declare the assets in `pubspec.yaml`.
2. `lib/core/i18n/i18n.dart`: load the two JSON assets at startup (before first frame, alongside
   splash); export `t(key, {params})` matching the web helper's interpolation syntax EXACTLY
   (mirror the implementation you read — same placeholder format, same missing-key behaviour).
   Locale follows the device; manual override stored in settings later.
3. Mobile-only strings (e.g. "Unlock with fingerprint") go in the SAME two web JSON files under a
   `mobile.` namespace — one source of truth, then re-sync. The parity checker covers them for
   free.
4. Extend `apps/web/scripts/check-i18n-parity.mjs`: also scan `apps/mobile/lib` for `t('...')` /
   `t("...")` usages so unused/missing mobile keys are build-blocking, same as web.

## Task C — Money port

1. `lib/core/money/money.dart`: port `apps/web/src/lib/money.ts` function-for-function. Integer
   minor units on the wire and in state (`int`, never `double` — `flutter-lessons` issue 8);
   format/parse only at the edge. Use `intl`'s `NumberFormat` — VERIFY its `ar-EG` currency
   layout and digit choice against web's output at execution time; any deviation or polyfill
   decision goes to DECISIONS, not silently into code.
2. Fixture generation: a small Node script (or manual run) executes web's `money.ts` against ~30
   representative amounts (EGP + at least one other currency, ar-EG + en, including 0, negatives,
   large values) and writes `apps/mobile/test/fixtures/money_fixtures.json`.
3. `test/core/money_test.dart`: table-driven — Dart output must equal the web fixture table
   byte-for-byte.

## Task D — Theme

1. `lib/core/theme/app_theme.dart`: build light/dark `ThemeData` + a `ConductorTokens`
   `ThemeExtension` from the generated token classes. Type theme uses the bundled fonts and
   `TokenType` sizes. Components read tokens via `Theme.of(context).extension<ConductorTokens>()`
   (or a `context.tokens` helper) — ALL mobile styling flows through this from now on; no hex
   literal will ever appear outside `tokens.dart` (session 19 adds a grep gate for `Color(0x`).
2. `MaterialApp(themeMode: ThemeMode.system)` now consumes these themes; delete the session-01
   placeholders.

---

## Smoke Test

- [ ] `node scripts/generate-mobile-tokens.mjs` produces `tokens.dart`; running it twice is
      idempotent; `--check` passes clean and fails after a manual temp edit (revert it)
- [ ] `node scripts/sync-mobile-i18n.mjs` same: idempotent + `--check` drift detection
- [ ] Change a token in `tokens.css` on a scratch branch → regenerate → mobile placeholder screen
      shows the new colour (then discard the scratch change)
- [ ] `flutter test` green: money fixtures match for ar-EG and en, EGP amounts including 0,
      negatives, and large values
- [ ] Placeholder screen shows a translated key from `ar.json` in Arabic and flips with device
      language
- [ ] Parity checker fails when a key exists in `en.json` but not `ar.json` (test then revert),
      and catches a `t('mobile.bogus')` in mobile code (test then revert)
- [ ] `flutter analyze` 0 issues; `apps/web` `npx tsc --noEmit` and web parity check still green

## Risks

- `intl` ar-EG gaps vs web's `Intl.NumberFormat` output → Task C fixture verification catches it;
  resolution via DECISIONS.
- Interpolation-syntax mismatch between web `t()` and the Dart port → mirror the read
  implementation, add unit tests for every placeholder form web uses.

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file with _done
→ /compact → open FILE_03_MOBILE_AUTH_BACKEND.md
```
