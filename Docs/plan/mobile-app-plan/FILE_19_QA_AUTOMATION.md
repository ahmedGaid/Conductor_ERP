# SESSION 19 — QA Automation & Crash Monitoring
# Files: apps/mobile/integration_test/** (new), apps/mobile/test/** (gaps),
#        scripts/gates/ (mobile gate), CI config (READ what exists),
#        DECISIONS.md (crash-reporting entry)

**Objective:** the safety net that lets every future session (and every future release) ship
without fear: unit tests where logic lives, golden tests pinning the UI, E2E flows for the
golden paths, mechanical gates (hex ban, physical-direction ban, token drift, i18n parity) wired
into ONE command, and crash/ANR monitoring decided and installed. "Ready next day for launch
without bugs" is bought here, not hoped for.

---

## Before You Start

1. Inventory what tests already exist per session (money fixtures, link round-trips, queue
   logic, golden suite…) → the gap list, not a rewrite list.
2. Read current `patrol` docs (it wraps `integration_test` and adds native automation —
   permission dialogs, airplane-mode toggling; runs on emulator/simulator; CI-friendly). If
   patrol's native capabilities aren't needed for a flow, plain `integration_test` suffices —
   choose per flow.
3. READ the repo's CI setup (if any) → mobile jobs join the existing lane, not a parallel world.
   Note: `flutter test` runs on the Windows dev machine; E2E needs an emulator lane.
4. Crash reporting DECISION (session 01 deferred it): recommendation — **Sentry
   (`sentry_flutter`)**, self-hosted Sentry instance if the customer-hosted philosophy demands it
   at deployment time; the SDK is the same either way. PII scrubbing ON (no user names/amounts in
   breadcrumbs), obfuscated-build symbolication (`--obfuscate --split-debug-info` + symbol
   upload) verified. Write the entry, then install.

"Do not write anything yet."

---

## Task A — Unit + golden layer (`flutter test`)

Target LOGIC, not screenshots (goldens already pin the pixels): money port (exists — extend to
100% branch), i18n interpolation, token generator (`--check` fixture), `parseLink`/`linkFor`
round-trips, write-queue state machine (mock dio: replay, backoff, conflict, chain-stop),
upload-queue transitions, SSE event-splitter with adversarial chunk fixtures (session 14),
cache key scoping + eviction, `ApiFailure` mapping, bloc tests for the list/mutation patterns
(`flutter-lessons` 4–6 behaviours pinned: one emit per load, no Loading re-emit on mutation).
Golden suite: verify coverage — every design-system primitive and each module's key screen states
× RTL/LTR × light/dark. Fast (< 90 s), zero flake, no real network (mock at the datasource
boundary).

## Task B — Mechanical gates (`scripts/gates/` — join the house style, gate03 pattern)

One entry: `python scripts/gates/gate_mobile.py` (or extend gate03 — READ its structure and
follow the house convention) enforcing:
1. No raw `Color(0x` in `apps/mobile/lib` outside the generated `tokens.dart`
2. No physical directions: `EdgeInsets.only(left:|right:)`, `Alignment.centerLeft|centerRight`,
   `Positioned(left:|right:)`, `TextAlign.left|right` (allowlist file for the rare justified
   case, each line with a comment why)
3. Token drift: `generate-mobile-tokens.mjs --check` + `sync-mobile-i18n.mjs --check`
4. i18n parity incl. mobile keys (session 02's extension — verify it still covers new dirs)
5. `flutter analyze` 0 issues; unit + golden suite green; `npx tsc --noEmit` in `apps/web`
   still green (bridge scripts touched nothing)
6. No `print(` / `debugPrint(` left in release paths; no TODO without an issue ref

## Task C — E2E golden paths (`integration_test/`, patrol where native control needed)

Flows (each self-contained against a seeded dev backend — write the seed management command if
one doesn't exist; READ `erp/setup` first, seeding may exist):
1. `auth_test` — sign in ar → dashboard renders → sign out → data wiped assertion (relaunch
   lands on sign-in)
2. `invoice_test` — create invoice (picker, 2 lines) → submit → detail shows correct total →
   appears in list
3. `approvals_test` — seeded pending PO → swipe approve → gone from inbox → status changed
4. `offline_test` — airplane-mode toggle (patrol native automation) → create customer → pending
   chip → network on → synced assertion
5. `assistant_test` — open assistant → send seeded question → streamed answer appears
6. `ltr_smoke_test` — en device locale run of flows 1–2 (RTL is default everywhere else; this
   catches LTR regressions — the mirror of the usual industry problem)

Run cadence: full E2E on the release-candidate build before ANY store submission (session 20
bakes this into the runbook); gates + unit + goldens on every commit.

## Task D — Crash monitoring

Install per the DECISIONS entry: obfuscated release builds with symbol upload wired into the
build script, environment tags (staging/production), PII scrub config, alert route (email for
now). Verify a forced test crash arrives readable (symbolicated, correct app version) from BOTH
platforms' release builds.

---

## Smoke Test

- [ ] `python scripts/gates/gate_mobile.py` → green; then prove each check: plant a
      `Color(0xFF...)`, an `EdgeInsets.only(left:)`, a missing ar key, a token drift → four red
      runs → revert → green
- [ ] Unit + golden suite < 90 s, green, runs on the Windows dev machine
- [ ] All six E2E flows pass against the seeded backend on Android emulator; flows 1–3 also on
      iOS simulator (or a CI-built app on device — document which)
- [ ] Forced crash in an obfuscated release build → appears in the crash dashboard,
      symbolicated, no PII in the event payload
- [ ] CI (if repo has it): mobile gate + unit wired into the existing pipeline and red-blocking
- [ ] PARITY.md/PERF.md untouched by this session except QA rows flipped

## Risks

- E2E flake destroying trust → flows use `Key`-based finders (add keys where missing —
  surgical), generous waits on network steps, seeded deterministic data; a flow that flakes
  twice gets fixed or deleted, never retried-until-green.
- Golden drift across machines → goldens generated on one canonical environment (documented in
  the test README); CI compares on the same image.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_20_STORE_LAUNCH.md
```
