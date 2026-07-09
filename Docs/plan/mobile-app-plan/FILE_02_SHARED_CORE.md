# SESSION 2 — Shared Core Package
# Files: packages/core/** (new), scripts/generate-mobile-tokens.mjs (new, repo root),
#        apps/web/scripts/check-i18n-parity.mjs, apps/mobile/src/ui/theme.ts (new)

**Objective:** create `packages/core` — the single bridge between web truth and the mobile app:
design tokens generated from `tokens.css`, the shared `ar.json`/`en.json` strings, a
behaviour-identical `money` port, and shared API types. After this session, mobile literally
cannot have its own colours, strings, or money math.

**Why a generator, not a copy:** a copied token file diverges silently. A generated file makes
`tokens.css` mechanically authoritative — change a colour on web, run the script, mobile follows.

---

## Before You Start

1. Open `apps/web/src/styles/tokens.css` → read ALL custom properties; note naming groups
   (`--color-*`, spacing, radius, motion durations/easings, type scale).
2. Open `apps/web/src/lib/money.ts` → read fully; note every exported function, rounding rule,
   and locale behaviour (Arabic-Indic vs Latin digits — copy web's exact choice).
3. Open `apps/web/src/i18n/` → note how locales load and how keys are namespaced.
4. Open `apps/web/scripts/check-i18n-parity.mjs` → understand how it finds used keys.

"Do not write anything yet."

---

## Task A — Token generator

Create `scripts/generate-mobile-tokens.mjs` (repo root, plain Node, no deps):

1. Parse `apps/web/src/styles/tokens.css` with a regex over `--name: value;` declarations,
   capturing both the light (`:root`) and dark (`[data-theme="dark"]` or whatever selector the
   file actually uses — READ it) blocks.
2. Emit `packages/core/tokens.ts`:

```ts
// GENERATED from apps/web/src/styles/tokens.css — DO NOT EDIT. Run: node scripts/generate-mobile-tokens.mjs
export const light = { colorBg: "#...", colorText: "#...", /* every --color-* */ } as const;
export const dark  = { /* same keys, dark values */ } as const;
export const space = { /* spacing scale, numbers in dp */ } as const;
export const radius = { /* radii */ } as const;
export const motion = { /* durations (ms numbers) + easing curves */ } as const;
export const type = { /* font sizes/line heights as numbers */ } as const;
```

3. Convert `px`/`rem` to plain numbers (dp); keep hex strings as-is. Fail the script loudly if
   light/dark key sets differ.
4. Add a `--check` mode (regenerate to temp, diff against committed file, exit 1 on drift) and
   wire it into `scripts/gates/gate03.py`'s checklist if that gate has an extension point — else
   note it for the session-19 CI wiring.

## Task B — Shared i18n

1. `packages/core/i18n.ts`: import `apps/web/src/i18n/locales/ar.json` + `en.json` directly
   (workspace-relative import; `resolveJsonModule: true`). Export `t(key, params?)` matching the
   web helper's interpolation syntax exactly (READ the web implementation, mirror it).
2. Mobile-only strings (e.g. "Unlock with Face ID") go in the SAME two JSON files under a
   `mobile.` namespace — one source of truth, parity checker covers them for free.
3. Extend `check-i18n-parity.mjs`: also scan `apps/mobile/src` + `apps/mobile/app` for `t("...")`
   usages so unused/missing mobile keys are build-blocking, same as web.

## Task C — Money port

1. `packages/core/money.ts`: port `apps/web/src/lib/money.ts` function-for-function. Integer
   minor units on the wire; format/parse only at the edge. `Intl.NumberFormat` exists in RN's
   Hermes engine — VERIFY at execution time on both platforms; if a gap exists (e.g. `ar-EG`
   currency layout), the polyfill decision goes to DECISIONS, not silently into code.
2. `packages/core/money.test.ts`: table-driven tests asserting mobile output equals a fixture
   table generated from the web implementation (create the fixture by running web's money.ts in
   Node against ~30 representative amounts, EGP + at least one other currency, both locales).

## Task D — API types + theme hook

1. `packages/core/api-types.ts`: shared request/response interfaces for the endpoints mobile will
   consume. Start with what session 04 needs (auth, dashboard, list envelopes/pagination shape —
   READ how `apps/web/src/api/*.ts` types responses and reuse/move those types here where
   practical without breaking web imports; re-export from the old location if needed).
2. `apps/mobile/src/ui/theme.ts`: `useTheme()` hook — reads OS scheme via RN `useColorScheme()`,
   returns `light`/`dark` token object. ALL mobile styling flows through this hook from now on;
   no hex literal will ever appear in `apps/mobile/src` (session 19 adds a lint/grep gate for it).

---

## Smoke Test

- [ ] `node scripts/generate-mobile-tokens.mjs` produces `packages/core/tokens.ts`; running it
      twice is idempotent; `--check` passes clean and fails after a manual temp edit (revert it)
- [ ] Change a token in `tokens.css` on a scratch branch → regenerate → mobile placeholder screen
      shows the new colour (then discard the scratch change)
- [ ] `money.test.ts` green: mobile formatting === web fixture table, ar-EG and en, EGP amounts
      including 0, negatives, and large values
- [ ] Placeholder screen shows a translated key from `ar.json` in Arabic and flips with device
      language
- [ ] Parity checker fails when a key exists in `en.json` but not `ar.json` (test then revert),
      and catches a `t("mobile.bogus")` in mobile code (test then revert)
- [ ] `npx tsc --noEmit` green in BOTH `apps/mobile` and `apps/web` (moved types broke nothing)

## Risks

- `Intl` gaps in Hermes for `ar-EG` → Task C verification step; polyfill only via DECISIONS.
- Type moves breaking web → re-export shims from original paths; web tsc in the smoke test.

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file with _done
→ /compact → open FILE_03_MOBILE_AUTH_BACKEND.md
```
