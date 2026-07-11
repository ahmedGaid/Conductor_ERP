# SESSION 1 — Decisions & Scaffold
# Files: DECISIONS.md, apps/mobile/** (new), apps/mobile/PARITY.md (new)

**Objective:** make the architecture decisions binding (DECISIONS.md), create the Flutter app
under `apps/mobile`, lock strictness (analysis_options), and prove it runs on a real Android
device and an iOS simulator/device. Nothing product-shaped yet — just a running, lint-strict,
RTL-defaulted shell with the fonts bundled.

**Why this order:** every later session imports from this scaffold. Getting project layout,
lint strictness, RTL default, and fonts right NOW prevents 20 sessions of drift.

---

## Prerequisites (verify before starting — stop if missing)

- Flutter stable SDK installed (`flutter doctor` clean for Android toolchain), a physical
  Android device or emulator.
- An iOS path: either a Mac with Xcode, or a Codemagic account wired to this repo (iOS cannot be
  built from Windows locally — CI cloud builds are the expected path from this machine). If
  neither exists yet, STOP: choosing/setting up the iOS build path is a founder decision that
  gates session 20 hard and this session's iOS smoke.
- Recall the **`flutter-lessons`** skill (issue→fix catalog) — its patterns are cited by name
  throughout this plan.

---

## Before You Start

1. Open `DECISIONS.md` → read the last 5 entries → match their format exactly.
2. Open `Docs/ARP_STRATEGY.md` §5 → re-confirm the module scope freeze is still standing.
3. Open `apps/web/index.html` / the web CSS `@font-face` rules → note the EXACT font families and
   weights web ships (IBM Plex Sans Arabic + Inter) — mobile bundles the same ones.
4. Run `flutter --version` → note the pinned SDK version for the DECISIONS entry.

"Do not write anything yet."

---

## Task A — DECISIONS entries (write these FIRST, code second)

Append to `DECISIONS.md`, matching its format, six entries:

1. **Mobile stack: Flutter (pinned stable SDK, Dart 3).** Native AOT performance + Impeller
   rendering for low-end Androids, pixel-identical brand across OEM skins, first-class RTL,
   Dukkan-proven team fluency (Clean Architecture + `flutter_bloc` + `get_it` + `go_router`).
   Rejected: React Native + Expo (perf ceiling on low-end devices, per-OEM rendering drift —
   its TS-reuse advantage replaced by generators), Swift+Kotlin twin codebases (team size),
   Capacitor/webview (violates native-first bar). Accepted costs recorded: no TS type sharing;
   iOS builds via Mac or Codemagic; SDK pinned — upgrades are deliberate, one session each.
2. **Approved dependency list for `apps/mobile`** (the ONLY pre-approved list; anything else asks
   first): `flutter_bloc`, `equatable`, `get_it`, `go_router`, `dio`, `drift` (+
   `sqlite3_flutter_libs`, `drift_dev`/`build_runner` dev-only), `flutter_secure_storage`,
   `local_auth`, `mobile_scanner`, `image_picker`, `file_picker`, `share_plus`, `path_provider`,
   `firebase_messaging` (+ `firebase_core`) — messaging transport ONLY (entry 6), `intl`.
   Dev/QA: `integration_test` (SDK), `patrol`, golden toolkit decision in session 05;
   `sentry_flutter` **pending** a separate crash-reporting decision in session 19
   (customer-hosted philosophy applies to customer data; crash telemetry needs its own entry).
   Explicitly banned: `internet_connection_checker` (see `flutter-lessons` issue 1) — network
   probing is hand-rolled `dart:io HttpClient` HEAD probes.
3. **One API.** Mobile consumes existing endpoints; only auth/device/push endpoints are added.
   No business logic on-device. Conflicts: server wins, surfaced to the user.
4. **Brand sources stay single.** `tokens.css` → generated `lib/core/theme/tokens.dart`; shared
   `ar.json`/`en.json` synced into mobile assets with a drift check; icon set ported by hand from
   `icons.tsx` to `CustomPainter` paths; fonts bundled in-binary.
5. **Release policy: store releases only — no OTA code push.** No Shorebird or equivalent. An app
   holding a company's books has no code-delivery channel outside store review. Hotfix latency is
   handled by staged rollout + halt criteria (session 20).
6. **Push transport: FCM messaging-only.** `firebase_messaging` for APNs/FCM delivery; no
   Firestore, no Firebase Analytics, no other Firebase products. Payloads carry record IDs and
   the visible notification text only — never business data beyond what the user is shown.

## Task B — Flutter scaffold

```
cd apps
flutter create --org com.conductor --project-name conductor_arp mobile
```

Then, inside `apps/mobile`:

1. `pubspec.yaml`: add approved deps from Task A only (skip camera/push/scanner until their
   sessions if you prefer lean installs — but the DECISIONS list is the ceiling either way).
   Set `environment.sdk` to the pinned Dart range. App name **Conductor**.
2. `analysis_options.yaml`: base on `flutter_lints`, then tighten — enable at minimum
   `prefer_const_constructors`, `prefer_const_literals_to_create_immutables`,
   `directives_ordering`, `avoid_print`, `always_declare_return_types`,
   `unawaited_futures`/`discarded_futures`, `use_build_context_synchronously`.
   `flutter analyze` at 0 issues is a standing gate from this session on.
3. Platform config: Android `applicationId com.conductor.arp` (minSdk per current Flutter
   default, check `flutter-lessons`-era devices still covered); iOS bundle id
   `com.conductor.arp`; deep-link scheme `conductor` registered on both platforms (session 06
   wires routes); app display name **Conductor** (Arabic store name handled in session 20).
4. Fonts: copy IBM Plex Sans Arabic + Inter (the exact weights web uses — from Before-You-Start
   read 3) into `apps/mobile/assets/fonts/`; declare families in `pubspec.yaml`; set the default
   `TextTheme` families in a placeholder theme. No system-font fallback flash — fonts are
   in-binary, available from first frame.
5. Dark mode: `MaterialApp(themeMode: ThemeMode.system)` with placeholder light/dark themes
   (session 02 replaces them with token-built `ThemeExtension`s).
6. Folder skeleton (empty barrel files are fine) — Clean Architecture, the Dukkan-proven shape:

```
apps/mobile/
├── lib/
│   ├── core/
│   │   ├── theme/       # tokens.dart (generated, session 02), app_theme.dart
│   │   ├── icons/       # CustomPainter port of icons.tsx (session 05)
│   │   ├── i18n/        # t() helper + loader (session 02)
│   │   ├── money/       # money.dart port (session 02)
│   │   ├── network/     # HTTP-probe NetworkInfo (session 04; flutter-lessons issue 1)
│   │   ├── di/          # get_it wiring (session 04 on; flutter-lessons issue 7 order)
│   │   ├── router/      # go_router (session 06)
│   │   └── errors/      # failure taxonomy (session 04)
│   ├── domain/          # entities, repository interfaces, use cases
│   ├── data/            # models, datasources (dio remote / drift local), repo impls
│   └── presentation/    # blocs, pages, widgets
├── assets/fonts/
├── assets/i18n/         # synced ar.json/en.json (session 02)
├── test/                # unit + widget; test/goldens/ from session 05
├── integration_test/    # session 19
├── PARITY.md
├── analysis_options.yaml
└── pubspec.yaml
```

Layer rules (binding from day 1): `domain/` never imports `data/`; pages/widgets hold no
business logic (BLoC events); BLoCs call use cases, never repositories directly; side effects in
`BlocListener` only (`flutter-lessons` issue 6).

## Task C — PARITY.md ledger

Create `apps/mobile/PARITY.md`: a table with one row per web capability. Build the row list by
walking `apps/web/src/pages/` (and the web nav) at execution time — do NOT trust this plan's
module list. Columns: `Area | Web capability | Mobile status (todo/partial/done/deferred+reason) |
Session`. Every later session updates its rows; session 21 audits it.

---

## Smoke Test

- [ ] `flutter run` → app opens on Android device/emulator showing a placeholder screen in
      IBM Plex Sans Arabic (Arabic sample string renders in the correct font, not system fallback)
- [ ] Same on iOS simulator (Mac) or a Codemagic-built dev artifact installs and opens on an iPhone
- [ ] Device set to Arabic → layout direction is RTL (check with a temporary `Row` of two labeled
      boxes using `EdgeInsetsDirectional`: "start" box appears on the right)
- [ ] Dark mode: flipping OS appearance flips the placeholder background (`ThemeMode.system` works)
- [ ] `flutter analyze` → 0 issues; `flutter test` → the default smoke test passes
- [ ] `DECISIONS.md` has the six entries; `PARITY.md` exists with real rows from the live web nav
- [ ] Repo root `python scripts/gates/gate03.py` still green (mobile scaffold must not trip web
      gates) and `apps/web` `npx tsc --noEmit` untouched-still-green

## Risks

- iOS build path unresolved (no Mac, no Codemagic) → prerequisite stop-condition; don't start
  session 02 with the iOS question open.
- Flutter SDK / plugin API drift since plan authorship → pin versions in the DECISIONS entry;
  read current docs for any config that fails.

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file with _done
→ Type /compact in Claude Code
→ Open FILE_02_SHARED_CORE.md and continue
```
