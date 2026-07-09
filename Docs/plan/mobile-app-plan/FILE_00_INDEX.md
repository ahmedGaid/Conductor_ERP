# Conductor ARP Mobile — Master Index

> **STATUS: FUTURE PLAN — NOT SCHEDULED.** This folder is written ahead of time on purpose and is
> **not** part of the current roadmap (`Docs/plan/arp-roadmap.md`). Do not start session 01 until a
> DECISIONS entry activates this plan (expected slot: after Phase B "month-close" proves the
> flagship, or when a paying customer demands mobile). When activated, re-verify every "Before You
> Start" read — the web codebase will have moved since this plan was written (2026-07-04).

## Project Goal

Ship **Conductor ARP itself on iOS and Android** — not a companion app, not a wrapped webview.
One product, five surfaces (web, desktop browser, Android, iPhone, tablet), identical
capabilities, identical permissions, identical AI, identical brand. A user moving from desktop to
phone should feel zero product boundary — the same way Linear, Slack, and ChatGPT feel like one
product everywhere. Quality bar: **Linear's craft, Telegram's calm** — on a phone.

**Parity means parity with what exists.** The web product deliberately has no HR, manufacturing,
or projects (scope freeze, `Docs/ARP_STRATEGY.md` §5). Mobile mirrors the real module list:
dashboard, sales, purchasing, inventory, accounting, CRM, pricing, e-invoice, workflow/approvals,
notifications, AI workspace, settings/administration. When web grows, mobile grows — the parity
ledger (session 01 creates `apps/mobile/PARITY.md`) is the contract.

## Architecture (the five standing decisions)

1. **React Native + Expo, TypeScript.** Truly native rendering (not a webview — satisfies
   "native first"), while reusing the existing TS investment: API types, i18n JSON files, token
   values, money discipline, and Claude Code's fluency in this repo's language. Native
   Swift+Kotlin = two codebases this team cannot carry; Flutter = zero reuse and a second token
   pipeline. Justification recorded in DECISIONS before session 01 writes code.
2. **One API.** Mobile consumes the SAME Django endpoints as web. The only mobile-specific
   backend additions are auth tokens, device registry, and push registration (session 03). No
   business logic ever lives on the phone — contracts, validation, RBAC, and audit stay
   server-side, so parity of rules is automatic, not maintained.
3. **Single sources of truth for brand.** `tokens.css` stays the only home of raw hex — a build
   script generates `tokens.ts` from it. `ar.json`/`en.json` stay the only home of strings — the
   mobile bundle imports the same files and the parity checker covers mobile keys. The icon set is
   ported from `src/app/icons.tsx` to `react-native-svg` — same single-stroke hand, no icon
   library. Fonts (IBM Plex Sans Arabic + Inter) are bundled in the binary — no CDN.
4. **Offline = read cache + write queue.** SQLite read cache (stale-while-revalidate) makes every
   list/detail screen work on bad networks; a durable write queue with idempotency keys replays
   mutations when back online; conflicts are never silently merged — server wins and the user is
   shown what happened (blame-free, designed state). Drafts and AI threads are server-side
   already, which is what makes desktop→phone→tablet continuity free.
5. **Arabic/RTL is the default, again.** RTL is not a "supported mode" — it is the primary
   layout, tested first in every session, with LTR as the mirror. Same rule as web.

## Phases

| Phase | Sessions | Delivers |
|---|---|---|
| **0 — Foundations** | 01–04 | Decisions + scaffold, shared core (tokens/i18n/money), mobile auth backend, API client + read cache |
| **1 — Shell** | 05–07 | Design system primitives, navigation shell + deep links, sign-in + biometric lock |
| **2 — Modules** | 08–13 | Dashboard/reports, sales, purchasing + approvals, inventory + barcode, accounting views, attachments + camera |
| **3 — Intelligence & resilience** | 14–16 | AI workspace parity, push notifications, offline writes + sync |
| **4 — Launch quality** | 17–20 | Performance + accessibility, security hardening, QA automation, store launch |
| **Close** | 21 | Acceptance + regression + parity sign-off |

## Session Map

| # | File | What gets built | Est. |
|---|---|---|---|
| 01 | FILE_01_DECISIONS_AND_SCAFFOLD.md | DECISIONS entries, `apps/mobile` Expo scaffold, PARITY.md ledger, runs on device | 30 min |
| 02 | FILE_02_SHARED_CORE.md | `packages/core`: tokens.css→tokens.ts generator, shared i18n, money port, API types | 30 min |
| 03 | FILE_03_MOBILE_AUTH_BACKEND.md | Django: access/refresh tokens, device registry, remote logout, push-token endpoint | 30 min |
| 04 | FILE_04_API_CLIENT_AND_CACHE.md | Typed fetch client, auth interceptor, SQLite read cache, stale-while-revalidate | 30 min |
| 05 | FILE_05_DESIGN_SYSTEM.md | Text/Button/Input/Card/Sheet/Toast/ListRow + designed empty/error/loading, dark mode, RTL | 30 min |
| 06 | FILE_06_NAVIGATION_SHELL.md | expo-router tabs+stacks, monochrome chrome, deep-link scheme, tablet split view | 30 min |
| 07 | FILE_07_SIGN_IN_AND_LOCK.md | Login, secure token storage, Face ID/Touch ID/Android biometric lock, expiry UX | 25 min |
| 08 | FILE_08_DASHBOARD_AND_REPORTS.md | Dashboard cards, report list + viewer, period picker, number typography | 30 min |
| 09 | FILE_09_SALES.md | Customers + invoices: list/detail/create, statuses, money at the edge | 30 min |
| 10 | FILE_10_PURCHASING_AND_APPROVALS.md | Suppliers, POs, approvals inbox with swipe approve/reject + undo | 30 min |
| 11 | FILE_11_INVENTORY_AND_BARCODE.md | Items, stock levels, barcode/QR scanning via camera into search + receiving | 30 min |
| 12 | FILE_12_ACCOUNTING_VIEWS.md | Ledger, trial balance, bank reconciliation status — read views + drill-down | 30 min |
| 13 | FILE_13_ATTACHMENTS_AND_CAMERA.md | Document capture, upload queue, image/PDF viewer, share-sheet import | 30 min |
| 14 | FILE_14_AI_WORKSPACE.md | Full assistant parity: threads, SSE streaming, context envelope, action cards | 30 min |
| 15 | FILE_15_NOTIFICATIONS.md | Push (APNs/FCM via Expo), notification inbox parity, deep links into records | 30 min |
| 16 | FILE_16_OFFLINE_WRITES.md | Durable write queue, idempotency keys, conflict surfacing, background sync | 30 min |
| 17 | FILE_17_PERFORMANCE_AND_A11Y.md | Cold start budget, list virtualization, screen readers ar/en, dynamic type, reduced motion | 30 min |
| 18 | FILE_18_SECURITY_HARDENING.md | Cert pinning, root/jailbreak detection, screen privacy, session mgmt, audit hooks | 30 min |
| 19 | FILE_19_QA_AUTOMATION.md | Maestro E2E flows, unit tests, offline/sync test rig, crash reporting | 30 min |
| 20 | FILE_20_STORE_LAUNCH.md | EAS build profiles, store listings ar/en, beta program, phased rollout, OTA policy | 30 min |
| 21 | FILE_21_ACCEPTANCE.md | Parity ledger green, regression, brand-feel checklist, sign-off | 30 min |

Each phase boundary is a natural checkpoint: finish the phase, merge, start fresh sessions.

## Affected files (exhaustive)

New (the app):
- `apps/mobile/` — entire Expo app: `app/` (expo-router routes), `src/ui/` (design system),
  `src/api/`, `src/offline/`, `src/auth/`, `src/assistant/`, `src/icons/`, `assets/fonts/`,
  `PARITY.md`, `app.json`, `eas.json`
- `packages/core/` — shared TS: `tokens.ts` (generated), `i18n.ts`, `money.ts`, `api-types.ts`
- `apps/web/scripts/generate-mobile-tokens.mjs` (or repo-root script) — tokens.css → tokens.ts

Touched (existing):
- `erp/identity/` — token auth, device registry, push tokens (sessions 03, 15, 18)
- `erp/notifications/` — push fan-out (session 15)
- `apps/web/scripts/check-i18n-parity.mjs` — extend to mobile key usage (session 02)
- `DECISIONS.md` — new-dependency + architecture entries (session 01)
- Root `package.json` / workspace config — monorepo wiring (session 01)

## Never touch

- `apps/web/src/styles/tokens.css` values — mobile READS them via the generator; never forks them
- `apps/web/src/lib/money.ts` semantics — the mobile port must behave identically (shared tests)
- `erp/audit/models.py` — append-only; write only via `erp.audit.services.record(...)`
- Any module `contracts.py` signatures — mobile calls existing APIs; it never gets special ones
- Business logic placement — **no validation/pricing/posting rules on the device, ever**
- Web app behaviour — every backend change is additive; web keeps working untouched

## Ground Rules (every session)

1. **Read before write.** Sessions start by reading the named files — including re-checking web
   code that may have changed since this plan was written. Never write from memory.
2. **One product.** Before building any screen, open the same screen on web. Same terminology
   (Identity System §6 — one Arabic word per concept), same statuses, same empty states, same
   ordering. If mobile needs a term web doesn't have, add it to the Identity System first.
3. **Hard rules carry over:** tokens only (via generated `tokens.ts`), every string a key in BOTH
   `ar.json` and `en.json`, monochrome chrome, own icons only, designed states, settled motion
   from the token scale, reduced-motion honoured, money as integer minor units formatted at the edge.
4. **RTL first.** Every screen is built and smoke-tested in Arabic RTL before English LTR.
5. **New dependencies only from the session-01 DECISIONS list.** Anything beyond it = stop and ask.
6. **AI runs as the user; writes are human-in-the-loop** — same as web. The phone adds capture
   surfaces (camera, barcode, share sheet), never new authority.
7. **Gates before "done":** `npx tsc --noEmit` in `apps/mobile`, i18n parity script, mobile unit
   tests, and the session's smoke test on BOTH an Android device/emulator and an iOS
   device/simulator (macOS or EAS cloud build required for iOS — see session 01 prerequisites).
8. **Done means renamed.** Smoke test + gates pass, work committed → rename the session file with
   `_done`. A `_done` file is never reopened; next session = lowest-numbered file without suffix.
9. **Update PARITY.md every session.** Each shipped screen flips its ledger row. Acceptance
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

*Generated by ag-plan skill. Do not edit this index manually.*
