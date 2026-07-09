# SESSION 20 — Store Launch
# Files: apps/mobile/eas.json, app.json (store metadata), apps/mobile/store/** (new: listings,
#        screenshots plan, privacy answers), apps/mobile/RELEASE.md (new runbook)

**Objective:** everything between "the app works" and "the app is on both stores": build
profiles, signing, store listings in Arabic-first + English, privacy declarations, review-team
notes, a beta program, a phased rollout, and the OTA update policy that governs every release
after this one. Output includes `RELEASE.md` — the runbook any future session follows to ship.

**Prerequisites (start the clocks EARLY — these gate everything):** Apple Developer Program
enrollment (org, not individual — D-U-N-S takes days/weeks) and Google Play Console account.
If not done, do the applications FIRST, then build the session around the wait.

---

## Before You Start

1. Read current EAS Build + Submit + Update docs (this surface changes fastest of anything in
   the plan).
2. Recall `conductor-brand` + open `Docs/Brand/` Identity System → store listings are an
   off-app brand surface; the Identity System owns them. Wordmark/icon assets come from there —
   the app icon is the brand mark per Identity System rules (monochrome discipline applies).
3. Read both stores' CURRENT data-safety/privacy questionnaire formats.
4. Session 19's `RELEASE`-gating rule (full E2E before any submission/OTA).

"Do not write anything yet."

---

## Task A — Build & signing (`eas.json`)

1. Profiles: `development` (dev client), `staging` (internal distribution, staging backend URL,
   crash env=staging), `production` (store, production URL). Env-specific config via EAS env —
   the base URL NEVER hardcoded in source.
2. Signing: iOS via EAS-managed credentials; Android keystore EAS-managed with a **documented,
   secured backup** (losing it = losing the store listing — RELEASE.md gets a red-letter
   section). Version scheme: `1.0.0` + auto-increment build numbers via EAS.
3. `expo-updates` (OTA): channel per profile. **OTA policy (write into RELEASE.md + DECISIONS):**
   OTA for JS-only fixes after the SAME E2E suite passes; anything touching native modules/
   permissions/SDK = store release; staged OTA (staging channel bakes ≥ 24 h before production
   push); every OTA carries a rollback plan (republish previous bundle).

## Task B — Store presence (`apps/mobile/store/`)

1. Listings, Arabic first, English second: name ("كوندكتور — Conductor"), subtitle, description
   — written in the brand voice (quiet, precise; NO feature-grid hype — STRATEGY rule 6 applies
   to store copy too), keywords. Category: Business.
2. Screenshots: plan and produce per Identity System — real product screens (Arabic UI) on
   device frames, one calm caption each; phone + tablet sets; light mode primary. No fake data
   that could embarrass (seeded demo company with realistic Egyptian business data — build the
   demo seed alongside session 19's).
3. Privacy: data-safety forms answered from SECURITY.md's storage inventory (truthful: business
   data tied to account, crash data per DECISIONS, no ad tracking of any kind); privacy-policy
   URL (coordinate with whatever public web presence exists — if none, a minimal hosted policy
   page is a prerequisite task, flag it EARLY in the session).
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
   halt + assess; OTA rollback if JS-caused).
4. RELEASE.md runbook: the complete ordered checklist from "cut release branch" → gates → E2E →
   build → staging bake → submit/OTA → rollout gates → post-release monitoring → the
   store-review rejection playbook (common rejection causes + responses). Future releases follow
   THIS file — that's the deliverable.

---

## Smoke Test

- [ ] `staging` build installs on both platforms from EAS distribution, talks to staging
      backend, crash events tagged staging
- [ ] `production` builds pass store validation (upload to TestFlight processing + Play
      pre-launch report; fix what they flag — pre-launch report robo-test crawls without crash)
- [ ] OTA drill: trivial JS change → staging channel → visible on staging build after restart →
      promote to production channel on an internal build → rollback drill succeeds
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
- OTA misuse temptation (shipping native-adjacent changes as JS) → the policy line in DECISIONS
  is the contract; violating it strands users on broken bundles.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_21_ACCEPTANCE.md
```
