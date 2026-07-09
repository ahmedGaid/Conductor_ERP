# SESSION 6 — Navigation Shell & Deep Links
# Files: apps/mobile/app/** (expo-router routes), apps/mobile/src/ui/shell/** (new),
#        apps/mobile/src/navigation/links.ts (new)

**Objective:** the app's skeleton — tab + stack navigation mirroring the web nav's information
architecture, monochrome chrome, a universal deep-link scheme (`conductor://`) that every
notification and AI answer will use to land on exact records, and tablet split-view. Desktop
concepts translate here: sidebar → tabs + "more" sheet; cmd-K → search screen; peek panel → Sheet.

---

## Before You Start

1. Open the web app shell (`apps/web/src/app/AppShell.tsx`) → list the exact nav structure,
   order, and i18n keys of every section.
2. Open web routing (find the router config) → inventory route patterns per module — deep links
   must map 1:1 to these so links can be shared across devices.
3. Read current expo-router docs for: typed routes, linking config, and modal presentation.
4. Open `PARITY.md` → the module rows define which tabs/stacks exist.

"Do not write anything yet."

---

## Task A — Route tree (`app/`)

```
app/
├── _layout.tsx            # providers: theme, auth guard, i18n dir; splash release
├── (auth)/sign-in.tsx     # session 07 fills
├── (tabs)/
│   ├── _layout.tsx        # tab bar
│   ├── home/              # dashboard stack (session 08)
│   ├── sales/             # session 09
│   ├── inbox/             # approvals + notifications (sessions 10, 15)
│   ├── assistant/         # AI workspace (session 14)
│   └── more/              # every remaining module, settings, devices — a designed list, not a dump
├── search.tsx             # global search — full-screen modal, the cmd-K analogue
└── [module]/[id].tsx      # record screens pushed onto whichever stack is active
```

Tab choice reasoning: the five things a user reaches hourly (home, sales, approvals inbox,
assistant, everything-else). Verify against the live web nav during the read — if web's IA
changed, FOLLOW WEB, not this sketch. Tab bar: monochrome, own icons, active = weight/contrast
shift (never colour), labels from the same i18n keys web's nav uses.

## Task B — Chrome

1. Headers: RN large-title feel via a shared `ScreenHeader` (Text `title` variant, back arrow
   auto-flips in RTL — regression-test this explicitly; it was a real web bug).
2. Android back button + iOS swipe-back both work on every stack (expo-router default — verify,
   especially swipe-back in RTL which must come from the correct edge).
3. Screen transitions: token durations via the navigator's animation config; reduced-motion →
   fade-only.

## Task C — Deep links (`src/navigation/links.ts`)

1. Register scheme `conductor` (done in app.json session 01) + associated domains/app links for
   the future hosted domain (add the intent-filter/entitlement scaffolding now, values TBD).
2. `linkFor(entity, id)` + `parseLink(url)` — canonical map `conductor://sales/invoices/123` ↔
   web path `/sales/invoices/123`. One table drives both directions; unit-test round-trips.
3. Cold-start handling: link arrives before auth/hydration → stash target, navigate after unlock
   (session 07 hooks in). Unknown/no-permission targets → designed "not available" state, never
   a crash or blank.

## Task D — Tablet & landscape

1. Breakpoint from tokens (match web's sidebar breakpoint value): wide layout swaps tabs for a
   rail + two-pane (list | detail) using the same route tree — detail renders in the second pane
   instead of pushing. Keep this mechanism simple: a `useIsWide()` hook + a `TwoPane` component
   in `src/ui/shell/`; module sessions opt in per list screen.
2. iPad: enable multitasking sizes (no locked orientation); Android foldables get the same
   breakpoint behaviour for free. Hardware-keyboard basics on iPad: cmd-K opens search (RN
   key events — keep minimal, just search for now).

---

## Smoke Test

- [ ] Arabic RTL: tab order mirrors, back arrows point right, swipe-back from the correct edge
- [ ] Navigate every tab + a stub record screen; Android hardware back never exits unexpectedly
- [ ] `npx uri-scheme open "conductor://sales/invoices/1" --android` (and iOS equivalent) →
      app opens on the stub record screen; cold start (app killed) also works
- [ ] Link to a bogus module → designed "not available" state
- [ ] iPad/tablet emulator: wide layout shows rail + two panes; rotate → layout adapts live
- [ ] Reduced motion → transitions fade; parity + tsc green; PARITY.md nav rows flipped

## Risks

- expo-router API drift → docs read is load-bearing.
- RTL swipe-back edge cases on iOS → explicit smoke item; if broken, header back button is the
  guaranteed path and the issue is logged, not shipped silently.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_07_SIGN_IN_AND_LOCK.md
```
