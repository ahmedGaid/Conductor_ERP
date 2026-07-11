# Conductor ARP Mobile — Master Index

> **STATUS: FUTURE PLAN — NOT SCHEDULED.** This folder is written ahead of time on purpose and is
> **not** part of the current roadmap (`Docs/plan/arp-roadmap.md`). Do not start session 01 until a
> DECISIONS entry activates this plan (expected slot: after Phase B "month-close" proves the
> flagship, or when a paying customer demands mobile). When activated, re-verify every "Before You
> Start" read — the web codebase will have moved since this plan was written (2026-07-04, rebuilt
> on Flutter 2026-07-10).

## Project Goal

Ship **Conductor ARP itself on iOS and Android** — not a companion app, not a wrapped webview.
One product, five surfaces (web, desktop browser, Android, iPhone, tablet), identical
capabilities, identical permissions, identical AI, identical brand. A user moving from desktop to
phone should feel zero product boundary — the same way Linear, Slack, and ChatGPT feel like one
product everywhere. Quality bar: **Linear's craft, Telegram's calm** — on a phone. The app must
be a killer app on the four axes that matter: **performance** (instant on a ~150 USD Android),
**trust** (bank-grade device security, no code-injection update channels), **reliability**
(offline-first, crash-free ≥ 99.5%), and **UI/UX** (pixel-precise brand, golden-tested RTL).

**Parity means parity with what exists.** The web product deliberately has no HR, manufacturing,
or projects (scope freeze, `Docs/ARP_STRATEGY.md` §5). Mobile mirrors the real module list:
dashboard, sales, purchasing, inventory, accounting, CRM, pricing, e-invoice, workflow/approvals,
notifications, AI workspace, settings/administration. When web grows, mobile grows — the parity
ledger (session 01 creates `apps/mobile/PARITY.md`) is the contract.

## Architecture (the six standing decisions)

1. **Flutter (pinned stable SDK, Dart 3).** Truly native performance: Dart AOT-compiled, Impeller
   renderer, no JS bridge — holds 60 fps and fast cold starts on the low-end Androids Egyptian
   SMBs actually carry, and paints pixel-identically on every OEM skin (brand precision). RTL is
   first-class (`Directionality`, `EdgeInsetsDirectional`). The team already carries Flutter in
   production patterns via the Dukkan app — recall the **`flutter-lessons`** skill every session.
   Rejected: React Native + Expo (perf ceiling at the low end, per-OEM rendering drift; its TS
   reuse advantage is replaced by generators — see decision 4), Swift+Kotlin twin codebases (team
   size), any webview wrapper (violates native-first bar). Accepted costs, recorded honestly: no
   TS type sharing (Dart models are hand-written), iOS builds need a Mac or Codemagic CI (not
   buildable on Windows locally), no OTA updates (deliberate — decision 6). Architecture inside
   the app: Clean Architecture (`core/ domain/ data/ presentation/`) with `flutter_bloc` +
   `get_it` + `go_router` — the Dukkan-proven shape.
2. **One API.** Mobile consumes the SAME Django endpoints as web. The only mobile-specific
   backend additions are auth tokens, device registry, and push registration (session 03). No
   business logic ever lives on the phone — contracts, validation, RBAC, and audit stay
   server-side, so parity of rules is automatic, not maintained.
3. **Single sources of truth for brand.** `tokens.css` stays the only home of raw hex — a build
   script generates `lib/core/theme/tokens.dart` from it. `ar.json`/`en.json` stay the only home
   of strings — a sync script copies them into mobile assets with a drift check, and the parity
   checker covers mobile keys. The icon set is ported from `src/app/icons.tsx` to Flutter
   `CustomPainter` paths — same single-stroke hand, no icon library. Fonts (IBM Plex Sans Arabic
   + Inter) are bundled in the binary — no CDN.
4. **Offline = read cache + write queue.** `drift` (typed SQLite) read cache
   (stale-while-revalidate) makes every list/detail screen work on bad networks; a durable write
   queue with idempotency keys replays mutations when back online; conflicts are never silently
   merged — server wins and the user is shown what happened (blame-free, designed state). Drafts
   and AI threads are server-side already, which is what makes desktop→phone→tablet continuity
   free. Connectivity detection uses the HTTP-probe pattern from `flutter-lessons` (issue 1).
5. **Arabic/RTL is the default, again.** RTL is not a "supported mode" — it is the primary
   layout, tested first in every session, with LTR as the mirror. Same rule as web. Golden tests
   (session 05 onward) pin RTL + LTR × light + dark pixel-for-pixel.
6. **Store releases only — no OTA.** No over-the-air code push (no Shorebird, no equivalent).
   Every release goes through App Store / Play review with staged rollout. For an app that holds
   a company's books, "no code-delivery channel outside the stores" is a trust feature, not a
   limitation. Hotfix latency is mitigated by staged rollout + halt criteria (session 20).

## Phases

| Phase | Sessions | Delivers |
|---|---|---|
| **0 — Foundations** | 01–04 | Decisions + scaffold, brand bridge (tokens/i18n/money), mobile auth backend, API client + read cache |
| **1 — Shell** | 05–07 | Design system primitives + golden tests, navigation shell + deep links, sign-in + biometric lock |
| **2 — Modules** | 08–13 | Dashboard/reports, sales, purchasing + approvals, inventory + barcode, accounting views, attachments + camera |
| **3 — Intelligence & resilience** | 14–16 | AI workspace parity, push notifications, offline writes + sync |
| **4 — Launch quality** | 17–20 | Performance + accessibility, security hardening, QA automation, store launch |
| **Close** | 21 | Acceptance + regression + parity sign-off |

## Session Map

| # | File | What gets built | Est. |
|---|---|---|---|
| 01 | FILE_01_DECISIONS_AND_SCAFFOLD.md | DECISIONS entries, `apps/mobile` Flutter scaffold, strict lints, PARITY.md ledger, runs on device | 30 min |
| 02 | FILE_02_SHARED_CORE.md | Brand bridge: tokens.css→tokens.dart generator, i18n asset sync, money port + fixtures, theme | 30 min |
| 03 | FILE_03_MOBILE_AUTH_BACKEND.md | Django: access/refresh tokens, device registry, remote logout, push-token endpoint | 30 min |
| 04 | FILE_04_API_CLIENT_AND_CACHE.md | dio client, auth interceptor, drift read cache, stale-while-revalidate | 30 min |
| 05 | FILE_05_DESIGN_SYSTEM.md | AppText/AppButton/AppInput/AppCard/AppSheet/AppToast/ListRow + designed states, goldens, dark mode, RTL | 30 min |
| 06 | FILE_06_NAVIGATION_SHELL.md | go_router tabs+stacks, monochrome chrome, deep-link scheme, tablet split view | 30 min |
| 07 | FILE_07_SIGN_IN_AND_LOCK.md | Login, secure token storage, Face ID/Touch ID/Android biometric lock, expiry UX | 25 min |
| 08 | FILE_08_DASHBOARD_AND_REPORTS.md | Dashboard cards, report list + viewer, period picker, number typography | 30 min |
| 09 | FILE_09_SALES.md | Customers + invoices: list/detail/create, statuses, money at the edge | 30 min |
| 10 | FILE_10_PURCHASING_AND_APPROVALS.md | Suppliers, POs, approvals inbox with swipe approve/reject + undo | 30 min |
| 11 | FILE_11_INVENTORY_AND_BARCODE.md | Items, stock levels, barcode/QR scanning via camera into search + receiving | 30 min |
| 12 | FILE_12_ACCOUNTING_VIEWS.md | Ledger, trial balance, bank reconciliation status — read views + drill-down | 30 min |
| 13 | FILE_13_ATTACHMENTS_AND_CAMERA.md | Document capture, upload queue, image/PDF viewer, share-sheet import | 30 min |
| 14 | FILE_14_AI_WORKSPACE.md | Full assistant parity: threads, SSE streaming, context envelope, action cards | 30 min |
| 15 | FILE_15_NOTIFICATIONS.md | Push (FCM messaging-only), notification inbox parity, deep links into records | 30 min |
| 16 | FILE_16_OFFLINE_WRITES.md | Durable write queue, idempotency keys, conflict surfacing, resume/connectivity sync | 30 min |
| 17 | FILE_17_PERFORMANCE_AND_A11Y.md | Cold-start + frame budgets, list perf, screen readers ar/en, dynamic type, reduced motion | 30 min |
| 18 | FILE_18_SECURITY_HARDENING.md | Cert pinning, root/jailbreak detection, screen privacy, session mgmt, audit hooks | 30 min |
| 19 | FILE_19_QA_AUTOMATION.md | integration_test/patrol E2E flows, unit + golden suites, offline/sync test rig, crash reporting | 30 min |
| 20 | FILE_20_STORE_LAUNCH.md | Build/signing per platform, store listings ar/en, beta program, staged rollout, release runbook | 30 min |
| 21 | FILE_21_ACCEPTANCE.md | Parity ledger green, regression, brand-feel checklist, sign-off | 30 min |

Each phase boundary is a natural checkpoint: finish the phase, merge, start fresh sessions.

## Affected files (exhaustive)

New (the app):
- `apps/mobile/` — entire Flutter app: `lib/core/` (theme/tokens.dart generated, icons, money,
  i18n, network, di, router, errors), `lib/domain/` (entities, repo interfaces, use cases),
  `lib/data/` (models, datasources incl. drift cache + write queue, repo impls),
  `lib/presentation/` (blocs, pages, widgets), `assets/fonts/`, `assets/i18n/` (synced),
  `test/` + `test/goldens/` + `integration_test/`, `PARITY.md`, `pubspec.yaml`,
  `analysis_options.yaml`
- `scripts/generate-mobile-tokens.mjs` (repo root, plain Node) — tokens.css → tokens.dart
- `scripts/sync-mobile-i18n.mjs` (repo root, plain Node) — ar.json/en.json → mobile assets

Touched (existing):
- `erp/identity/` — token auth, device registry, push tokens (sessions 03, 15, 18)
- `erp/notifications/` — push fan-out (session 15)
- `apps/web/scripts/check-i18n-parity.mjs` — extend to mobile key usage (session 02)
- `DECISIONS.md` — new-dependency + architecture entries (session 01)

## Never touch

- `apps/web/src/styles/tokens.css` values — mobile READS them via the generator; never forks them
- `apps/web/src/lib/money.ts` semantics — the Dart port must behave identically (fixture tests)
- `erp/audit/models.py` — append-only; write only via `erp.audit.services.record(...)`
- Any module `contracts.py` signatures — mobile calls existing APIs; it never gets special ones
- Business logic placement — **no validation/pricing/posting rules on the device, ever**
- Web app behaviour — every backend change is additive; web keeps working untouched

## Ground Rules (every session)

1. **Read before write.** Sessions start by reading the named files — including re-checking web
   code that may have changed since this plan was written. Never write from memory.
2. **Recall the skills.** Every session recalls **`flutter-lessons`** (hard-won issue→fix
   catalog — offline/cache, BLoC flicker, DI order, money, RTL) and, for any UI work,
   **`conductor-brand`**. The lessons are load-bearing; re-learning them costs days.
3. **One product.** Before building any screen, open the same screen on web. Same terminology
   (Identity System §6 — one Arabic word per concept), same statuses, same empty states, same
   ordering. If mobile needs a term web doesn't have, add it to the Identity System first.
4. **Hard rules carry over:** tokens only (via generated `tokens.dart`), every string a key in
   BOTH `ar.json` and `en.json`, monochrome chrome, own icons only, designed states, settled
   motion from the token scale, reduced-motion honoured, money as integer minor units formatted
   at the edge (`double` for money is forbidden).
5. **RTL first.** Every screen is built and smoke-tested in Arabic RTL before English LTR.
   `EdgeInsetsDirectional` / `start/end` only — physical `left/right` forbidden.
6. **New dependencies only from the session-01 DECISIONS list.** Anything beyond it = stop and ask.
7. **AI runs as the user; writes are human-in-the-loop** — same as web. The phone adds capture
   surfaces (camera, barcode, share sheet), never new authority.
8. **Gates before "done":** `flutter analyze` (0 issues) and `flutter test` (all green, goldens
   included) in `apps/mobile`, i18n parity script, and the session's smoke test on BOTH an
   Android device/emulator and an iOS device/simulator (a Mac or Codemagic CI is required for
   iOS — see session 01 prerequisites).
9. **Done means renamed.** Smoke test + gates pass, work committed → rename the session file with
   `_done`. A `_done` file is never reopened; next session = lowest-numbered file without suffix.
10. **Update PARITY.md every session.** Each shipped screen flips its ledger row. Acceptance
    (session 21) fails if a row is neither green nor explicitly deferred with a written reason.

## How to use this plan

1. Activation: DECISIONS entry written, plan slot confirmed against the live roadmap.
2. New Claude Code session → paste `FILE_00_INDEX.md` + the next `FILE_NN` file.
3. Claude does the "Before You Start" reads, the tasks, then the smoke test on both platforms.
4. Smoke green → gates → commit → rename `_done` → `/compact` → next file in a fresh session.
5. One session file = one Claude session. Never roll two files into one chat.

## After all sessions complete

- Run FILE_21 acceptance end-to-end in both languages (Arabic RTL first), on phone AND tablet,
  online AND offline, light AND dark.
- Run the `conductor-brand` brand-feel checklist on every screen family.
- Submit via session 20's rollout plan (staged: internal → beta → 10% → 100%).
- Update the `erp-status` skill anchor; archive this folder's `_done` files into `erp-history`.

*Generated by ag-plan skill; rebuilt on Flutter 2026-07-10. Do not edit this index manually.*
