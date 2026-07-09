# SESSION 1 — Decisions & Scaffold
# Files: DECISIONS.md, package.json (root), apps/mobile/** (new), apps/mobile/PARITY.md (new)

**Objective:** make the architecture decisions binding (DECISIONS.md), create the Expo app under
`apps/mobile`, wire the monorepo, and prove it runs on a real Android device and an iOS
simulator/device. Nothing product-shaped yet — just a running, TypeScript-strict, RTL-defaulted
shell with the fonts bundled.

**Why this order:** every later session imports from this scaffold. Getting workspace wiring,
TS strictness, RTL default, and fonts right NOW prevents 20 sessions of drift.

---

## Prerequisites (verify before starting — stop if missing)

- Node ≥ 20, a physical Android device or emulator, and an iOS path: either a Mac with Xcode, or
  an Expo account with EAS builds enabled (iOS cannot be built from Windows locally — EAS cloud
  builds are the expected path from this machine).
- Expo account created; `npx expo login` works.

---

## Before You Start

1. Open `DECISIONS.md` → read the last 5 entries → match their format exactly.
2. Open root `package.json` → confirm whether npm workspaces are configured; note the current shape.
3. Open `apps/web/package.json` → note the TypeScript version and React version (mobile should not
   introduce a second TS major version).
4. Open `Docs/ARP_STRATEGY.md` §5 → re-confirm the module scope freeze is still standing.

"Do not write anything yet."

---

## Task A — DECISIONS entries (write these FIRST, code second)

Append to `DECISIONS.md`, matching its format, four entries:

1. **Mobile stack: React Native + Expo (TypeScript).** Native rendering, no webview. Rejected:
   Swift+Kotlin twin codebases (team size), Flutter (zero TS/token/i18n reuse), Capacitor webview
   (violates native-first bar). Expo SDK pinned; upgrades are deliberate, one session each.
2. **Approved dependency list for `apps/mobile`** (the ONLY pre-approved list; anything else asks
   first): `expo`, `expo-router`, `react-native-svg`, `expo-sqlite`, `expo-secure-store`,
   `expo-local-authentication`, `expo-camera`, `expo-notifications`, `expo-file-system`,
   `expo-document-picker`, `expo-haptics`, `@shopify/flash-list`, `expo-splash-screen`,
   `expo-updates`. Dev/QA tools: Maestro (E2E), `sentry-expo` **pending** a separate
   crash-reporting decision in session 19 (customer-hosted philosophy applies to customer data;
   crash telemetry needs its own entry).
3. **One API.** Mobile consumes existing endpoints; only auth/device/push endpoints are added.
   No business logic on-device. Conflicts: server wins, surfaced to the user.
4. **Brand sources stay single.** `tokens.css` → generated `tokens.ts`; shared `ar.json`/`en.json`;
   icon set ported by hand from `icons.tsx`; fonts bundled in-binary.

## Task B — Monorepo wiring

In root `package.json`, add npm workspaces (create the key if absent):

```json
"workspaces": ["apps/web", "apps/mobile", "packages/*"]
```

If `apps/web` was not previously a workspace member, verify `npm install` at root still leaves
`apps/web` building (`npx tsc --noEmit` there). If workspaces break web tooling, fall back to an
independent `apps/mobile` package (document the fallback in DECISIONS) — do not fight tooling for
a session.

## Task C — Expo scaffold

```
cd apps
npx create-expo-app@latest mobile --template blank-typescript
```

Then, inside `apps/mobile`:

1. Install the approved deps from Task A only (skip notifications/camera until their sessions if
   you prefer lean installs — but the DECISIONS list is the ceiling either way).
2. `tsconfig.json`: `"strict": true`, path alias `@core/*` → `../../packages/core/*` (package
   created next session — alias prepared now).
3. `app.json`: name **Conductor**, slug `conductor-arp`, scheme `conductor` (deep links), iOS
   bundle id `com.conductor.arp`, Android package `com.conductor.arp`,
   `"supportsRTL": true` and `"forcesRTL": false` under `expo.extra` per current Expo RTL guidance
   (READ current Expo docs at execution time — RTL config keys have moved between SDK versions),
   `userInterfaceStyle: "automatic"` (dark mode follows OS).
4. Fonts: copy IBM Plex Sans Arabic + Inter (the exact weights web uses — check
   `apps/web/index.html` / CSS `@font-face`) into `apps/mobile/assets/fonts/`; load via
   `expo-font` in the root layout; splash stays visible until fonts resolve
   (`expo-splash-screen`). No system-font fallback flash.
5. Folder skeleton (empty `index.ts` barrels are fine):

```
apps/mobile/
├── app/                 # expo-router routes (session 06 fills)
│   └── _layout.tsx      # fonts + providers + splash control
├── src/
│   ├── ui/              # design system (session 05)
│   ├── icons/           # ported icon set (session 05)
│   ├── api/             # client + endpoints (session 04)
│   ├── auth/            # tokens + biometrics (session 07)
│   ├── offline/         # sqlite cache + write queue (sessions 04, 16)
│   └── assistant/       # AI workspace (session 14)
├── assets/fonts/
├── PARITY.md
├── app.json
└── eas.json             # session 20 fills profiles; create empty stub
```

## Task D — PARITY.md ledger

Create `apps/mobile/PARITY.md`: a table with one row per web capability. Build the row list by
walking `apps/web/src/pages/` (and the web nav) at execution time — do NOT trust this plan's
module list. Columns: `Area | Web capability | Mobile status (todo/partial/done/deferred+reason) |
Session`. Every later session updates its rows; session 21 audits it.

---

## Smoke Test

- [ ] `npx expo start` → app opens on Android device/emulator showing a placeholder screen in
      IBM Plex Sans Arabic (Arabic sample string renders in the correct font, not system fallback)
- [ ] Same on iOS simulator, or an EAS development build installs and opens on an iPhone
- [ ] Device set to Arabic → layout direction is RTL (check with a temporary row of two labeled
      boxes: "start" box appears on the right)
- [ ] Dark mode: flipping OS appearance flips the placeholder background (automatic style works)
- [ ] `npx tsc --noEmit` passes in `apps/mobile`; `npx tsc --noEmit` in `apps/web` still passes
- [ ] `DECISIONS.md` has the four entries; `PARITY.md` exists with real rows from the live web nav
- [ ] Repo root `python scripts/gates/gate03.py` still green (mobile scaffold must not trip web gates)

## Risks

- Expo SDK / RTL config drift since plan authorship → the "read current docs" instruction in Task
  C is load-bearing.
- Workspaces breaking web builds → Task B fallback path, decided within the session.

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file with _done
→ Type /compact in Claude Code
→ Open FILE_02_SHARED_CORE.md and continue
```
