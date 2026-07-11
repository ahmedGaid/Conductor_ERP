# SESSION 20 — Store Launch
# Files: apps/mobile/android + ios signing/build config, apps/mobile/store/** (new: listings,
#        screenshots plan, privacy answers), apps/mobile/RELEASE.md (new runbook)

**Objective:** everything between "the app works" and "the app is on both stores": build
profiles, signing, store listings in Arabic-first + English, privacy declarations, review-team
notes, a beta program, and a phased rollout under the **store-only release policy** (no OTA —
session 01 decision 5) that governs every release after this one. Output includes `RELEASE.md` —
the runbook any future session follows to ship.

**Prerequisites (start the clocks EARLY — these gate everything):** Apple Developer Program
enrollment (org, not individual — D-U-N-S takes days/weeks), Google Play Console account, and
the iOS build path from session 01 (Mac or Codemagic) confirmed working for release builds.
If not done, do the applications FIRST, then build the session around the wait.

---

## Before You Start

1. Read current docs for the chosen iOS build path (Xcode signing on Mac, or Codemagic's
   Flutter workflow + managed code signing) and Play Console app-signing (Google-managed
   signing with an upload key).
2. Recall `conductor-brand` + open `Docs/Brand/` Identity System → store listings are an
   off-app brand surface; the Identity System owns them. Wordmark/icon assets come from there —
   the app icon is the brand mark per Identity System rules (monochrome discipline applies).
3. Read both stores' CURRENT data-safety/privacy questionnaire formats.
4. Session 19's release-gating rule (full E2E before any submission).

"Do not write anything yet."

---

## Task A — Build & signing

1. Flavors/configs: `development` (dev backend URL), `staging` (internal distribution, staging
   backend URL, crash env=staging), `production` (store, production URL) — via Flutter flavors
   (Android productFlavors + iOS schemes) with `--dart-define-from-file` per flavor. The base
   URL NEVER hardcoded in source.
2. Signing: Android — upload keystore with a **documented, secured backup** (losing it = losing
   the ability to update; Play App Signing holds the app key, but the upload key backup is
   still a red-letter RELEASE.md section) — plus Google-managed Play App Signing ON. iOS — via
   the chosen path (Xcode-managed certs on Mac, or Codemagic-managed). Version scheme: `1.0.0`
   + auto-increment build numbers in the build script.
3. Release builds: `flutter build appbundle --release --obfuscate --split-debug-info=...`
   (symbols uploaded to crash reporting per session 19) and `flutter build ipa` equivalents.
   **Release policy (write into RELEASE.md + reference the DECISIONS entry):** store releases
   only; no OTA channel exists. Hotfix path = expedited-review store release + staged-rollout
   halt; the runbook documents both stores' expedited-review request processes.

## Task B — Store presence (`apps/mobile/store/`)

1. Listings, Arabic first, English second: name ("كوندكتور — Conductor"), subtitle, description
   — written in the brand voice (quiet, precise; NO feature-grid hype — STRATEGY rule 6 applies
   to store copy too), keywords. Category: Business.
2. Screenshots: plan and produce per Identity System — real product screens (Arabic UI) on
   device frames, one calm caption each; phone + tablet sets; light mode primary. No fake data
   that could embarrass (seeded demo company with realistic Egyptian business data — build the
   demo seed alongside session 19's).
3. Privacy: data-safety forms answered from SECURITY.md's storage inventory (truthful: business
   data tied to account, crash data per DECISIONS, push via FCM transport — declare it,
   no ad tracking of any kind); privacy-policy URL (coordinate with whatever public web presence
   exists — if none, a minimal hosted policy page is a prerequisite task, flag it EARLY in the
   session).
4. Review-team notes + demo account: reviewers need a working login → dedicated demo tenant on
   a reachable staging server with seeded data; note explains B2B context, camera (barcode/
   documents) and notification (approvals) permission usage.

## Task C — Beta & rollout (`RELEASE.md`)

1. Beta: TestFlight internal → external group; Play internal testing → closed track. Recruit
   the real pilot customers (the Phase A/B companies from the roadmap). Feedback channel =
   whatever the team actually answers (WhatsApp group realistically) + crash dashboard triage
   rhythm.
2. Beta exit criteria (written, objective): ≥ 2 real companies using it daily for ≥ 2 weeks,
   crash-free sessions ≥ 99.5%, zero open P0/P1, approvals + invoice-create + assistant flows
   each used in anger by a non-developer.
3. Rollout: Play staged rollout 10% → 50% → 100% with 48 h crash-watch between steps; iOS
   phased release ON. Halt criteria defined (crash-free < 99% or any data-integrity report =
   halt + assess; with no OTA, the response to a bad release is halt-rollout + expedited-review
   fix — rehearse the timeline expectation honestly in the runbook).
4. RELEASE.md runbook: the complete ordered checklist from "cut release branch" → gates → E2E →
   build → staging bake → submit → rollout gates → post-release monitoring → the store-review
   rejection playbook (common rejection causes + responses) → the expedited-hotfix path. Future
   releases follow THIS file — that's the deliverable.

---

## Smoke Test

- [ ] `staging` build installs on both platforms (internal distribution: Play internal track /
      TestFlight internal or direct IPA), talks to staging backend, crash events tagged staging
- [ ] `production` builds pass store validation (upload to TestFlight processing + Play
      pre-launch report; fix what they flag — pre-launch report robo-test crawls without crash)
- [ ] Obfuscated-build crash symbolication verified on BOTH production-candidate builds
- [ ] Listings render correctly in both store consoles' previews, Arabic text direction correct
      everywhere (store consoles mangle RTL — verify visually)
- [ ] Demo/reviewer account: fresh device, reviewer-notes steps only → working session in < 2 min
- [ ] RELEASE.md dry-run: a person who didn't write it (or a fresh Claude session given only the
      file) can execute the release steps without asking questions
- [ ] Both apps SUBMITTED (or release-ready with submission blocked only on store-account
      formalities — state which, honestly, in the session report)

## Risks

- Store review rejections (B2B login-wall apps get flagged) → the demo account + notes ARE the
  mitigation; the rejection playbook in RELEASE.md handles round 2.
- No-OTA hotfix latency (days, not minutes) → staged rollout + 48 h crash-watch windows are the
  real safety net; never skip a bake window to ship faster.
- Upload-keystore loss → the red-letter backup section; verify the backup actually restores
  (test-sign with it once).

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_21_ACCEPTANCE.md
```
