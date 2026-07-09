# SESSION 19 — QA Automation & Crash Monitoring
# Files: apps/mobile/e2e/** (new, Maestro flows), apps/mobile/src/**/*.test.ts (gaps),
#        scripts/gates/ (mobile gate), .github/workflows or CI config (READ what exists),
#        DECISIONS.md (crash-reporting entry)

**Objective:** the safety net that lets every future session (and every future OTA update) ship
without fear: unit tests where logic lives, Maestro E2E flows for the golden paths, mechanical
gates (hex ban, physical-CSS-prop ban, token drift, i18n parity) wired into ONE command, and
crash/ANR monitoring decided and installed. "Ready next day for launch without bugs" is bought
here, not hoped for.

---

## Before You Start

1. Inventory what tests already exist per session (money fixtures, link round-trips, queue
   logic…) → the gap list, not a rewrite list.
2. Read current Maestro docs (it drives real builds via yaml flows; runs on emulator/simulator;
   CI-friendly). Confirm it can drive the Expo release build.
3. READ the repo's CI setup (if any) → mobile jobs join the existing lane, not a parallel world.
4. Crash reporting DECISION (session 01 deferred it): recommendation — **Sentry (sentry-expo)**,
   self-hosted Sentry instance if the customer-hosted philosophy demands it at deployment time;
   the SDK is the same either way. PII scrubbing ON (no user names/amounts in breadcrumbs),
   Arabic-locale symbolication verified. Write the entry, then install.

"Do not write anything yet."

---

## Task A — Unit layer (Jest via `jest-expo` — the standard, counts as approved tooling)

Target LOGIC, not screenshots: `packages/core` money (exists — extend to 100% branch),
i18n interpolation, token generator (`--check` fixture), `parseLink`/`linkFor` round-trips,
write-queue state machine (mock fetch: replay, backoff, conflict, chain-stop), upload-queue
transitions, cache key scoping + eviction, ApiError mapping. Fast (< 60 s), zero flake, no
native modules needed (mock expo-* at the boundary).

## Task B — Mechanical gates (`scripts/gates/` — join the house style, gate03 pattern)

One entry: `python scripts/gates/gate_mobile.py` (or extend gate03 — READ its structure and
follow the house convention) enforcing:
1. No raw hex in `apps/mobile/src` + `apps/mobile/app` (generated tokens import exempt)
2. No `marginLeft|marginRight|paddingLeft|paddingRight|left:|right:` style props (logical only;
   allowlist file for the rare justified case, each line with a comment why)
3. Token drift: `generate-mobile-tokens.mjs --check`
4. i18n parity incl. mobile keys (session 02's extension — verify it still covers new dirs)
5. `npx tsc --noEmit` both apps; unit suite green
6. No `console.log` left in release paths; no TODO without an issue ref

## Task C — E2E golden paths (`apps/mobile/e2e/*.yaml`, Maestro)

Flows (each self-contained against a seeded dev backend — write the seed management command if
one doesn't exist; READ `erp/setup` first, seeding may exist):
1. `auth.yaml` — sign in ar → dashboard renders → sign out → data wiped assertion (relaunch
   lands on sign-in)
2. `invoice.yaml` — create invoice (picker, 2 lines) → submit → detail shows correct total →
   appears in list
3. `approvals.yaml` — seeded pending PO → swipe approve → gone from inbox → status changed
4. `offline.yaml` — airplane-mode toggle (Maestro can via adb) → create customer → pending chip
   → network on → synced assertion
5. `assistant.yaml` — open assistant → send seeded question → streamed answer appears
6. `rtl-smoke.yaml` — en device locale run of flows 1–2 (RTL is default everywhere else; this
   catches LTR regressions — the mirror of the usual industry problem)

Run cadence: full E2E on the release-candidate build before ANY store submission or OTA push
(session 20 bakes this into the runbook); gates + unit on every commit.

## Task D — Crash monitoring

Install per the DECISIONS entry: release-build symbol upload in EAS build profile, environment
tags (staging/production), PII scrub config, alert route (email for now). Verify a forced test
crash arrives readable (symbolicated, correct app version) from BOTH platforms' release builds.

---

## Smoke Test

- [ ] `python scripts/gates/gate_mobile.py` → green; then prove each check: plant a hex, a
      `marginLeft`, a missing ar key, a token drift → four red runs → revert → green
- [ ] Unit suite < 60 s, green, runs on the Windows dev machine
- [ ] All six Maestro flows pass against the seeded backend on Android emulator; flows 1–3 also
      on iOS simulator (or EAS-built app on device — document which)
- [ ] Forced crash in a release build → appears in the crash dashboard, symbolicated, no PII in
      the event payload
- [ ] CI (if repo has it): mobile gate + unit wired into the existing pipeline and red-blocking
- [ ] PARITY.md/PERF.md untouched by this session except QA rows flipped

## Risks

- E2E flake destroying trust → flows use testID selectors (add them where missing — surgical),
  generous waits on network steps, seeded deterministic data; a flow that flakes twice gets
  fixed or deleted, never retried-until-green.
- Maestro/Expo version friction → pin versions; the E2E lane runs release-like builds, not Expo
  Go.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_20_STORE_LAUNCH.md
```
