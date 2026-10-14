# Admin Release Notes — plan index

**Goal (founder's words):** any update or release must be visible **inside the app to an Admin
user** — what is new, and *how to see/test it*. For a new feature: **what it is, why it matters to
users and the business, and how to test it**. Shown in **two places** (Settings **and** Help), with
a **detailed per-feature view**.

**One-line summary:** build the *admin-facing, bilingual, in-app "What's New"* layer on top of the
**version/release backbone that already exists** — do NOT build a second versioning system.

---

## What already exists (REUSE — do not rebuild)

Audited 2026-07-26. The release *infrastructure* is already here from twenty-harvest FILE_01–03:

| Piece | Where | Status |
|---|---|---|
| Version number (single source of truth) | root `VERSION` → `settings.CONDUCTOR_VERSION` | exists (⚠ stale: file says `1.0.0`, CHANGELOG top is `v1.1.0`) |
| Version exposed to app | `/health`, `/system-check`, `/api/system/status/` → `version` | exists |
| Version shown to Admin | Settings → System (`settings.system.version`, `SystemPage.tsx`) | exists |
| Developer changelog | root `CHANGELOG.md` (English, terse, dev bullets) | exists |
| Release steps (bump→changelog→tag→build) | `Docs/RUNBOOK.md` §Release + §7 RC definition + §8 E2E | exists |
| SemVer convention (`vMAJOR.MINOR.PATCH`) | used throughout | exists |
| Bilingual long-form content pattern | `apps/web/src/help/*` (`type L = {en;ar}`, prose in TS modules, chrome-only i18n keys) | exists — **this is the model for release-note content** |

## The gap (the NEW part = this plan)

Everything above is **developer/maintainer-facing**. There is **no** admin-facing, in-app,
bilingual "what changed, why it matters, how to test it" view. `CHANGELOG.md` is English dev bullets
in a file — a non-technical Admin or pilot customer can neither find it nor act on it.

This plan adds that one missing layer, reusing the version backbone and the Help content pattern.

---

## The three sessions (one file = one session)

| File | Session | Size | Model |
|---|---|---|---|
| `FILE_01_RELEASE_NOTES_DATA.md` | Release-note data model + seed v1.0.0/v1.1.0 + fix VERSION↔CHANGELOG drift + governance rule (SemVer intent, "a release is an intentional event") | Small–Medium | **Sonnet** (clear spec) |
| `FILE_02_WHATS_NEW_SURFACES.md` | In-app "What's New" — list view + per-feature deep-dive; wire into **Settings→System** and the **Help** area; designed states, brand/i18n/tokens | Medium | **Opus** (UI + brand judgment) |
| `FILE_03_RELEASE_WORKFLOW_AUTOMATION.md` | Light consistency check (VERSION↔CHANGELOG↔release data in sync), release checklist, reusable AI "draft release notes" workflow (human approves), RUNBOOK update | Small–Medium | **Sonnet** |

Writing each **future** release note (after this plan is built) is easy work → **Haiku**.

## Merge checkpoint

Off critical path. Merge to `main` after FILE_02 (the Admin can see it — the demo point), then
again after FILE_03 (automation + docs). Nothing here blocks handover.

---

## Data model (decided — see FILE_01 for the full type)

Release-note prose is **data**, authored in both languages via the existing `L = {en; ar}` type,
stored in a TS module **outside** the parity-checked i18n JSON (exactly how `help/content/*` works —
see the comment block at the top of `apps/web/src/help/types.ts`). Only the fixed chrome labels
("What's New", "Added", "Fixed", "Changed", "How to test", "Expected result", "Why it matters") are
i18n keys in `ar.json`/`en.json`.

```ts
type ChangeKind = "added" | "fixed" | "changed";
interface ReleaseChange   { kind: ChangeKind; summary: L; featureId?: string; }
interface ValidationScenario { name: L; steps: L[]; expected: L[]; }
interface ReleaseFeature  { id: string; title: L; whatItIs: L; whyItMatters: L; validation: ValidationScenario; }
interface Release {
  version: string;   // "1.1.0" — matches VERSION / CHANGELOG (no leading v in data)
  date: string;      // "2026-07-20"
  status: "candidate" | "released";
  headline: L;                    // one line: what this release is about
  changes: ReleaseChange[];       // Added / Fixed / Changed bullets
  features?: ReleaseFeature[];    // deep-dives for notable new features
  work?: { issues?: string[]; prs?: string[] };  // traceability (Linear IDs, PR #s)
  technical?: L;                  // optional maintainer note
}
```

This covers every item the founder asked for: Added/Fixed/Changed · what it is · why it matters to
users **and** business · how to test (numbered steps) · expected result · status · traceability.

## Decisions taken (rationale in each — record in `DECISIONS.md` during FILE_01)

- **Bundled data, not a backend model/DB.** The founder (or the AI, founder-approved) writes each
  note; nobody edits notes without a deploy. So no model, no migration, no API — leaner and matches
  the `help/content` precedent. A backend-editable version is a *future* option, only if customers
  ever need to author notes themselves. Not built now.
- **The in-app release note is the primary human artifact.** `CHANGELOG.md` stays as the short
  internal dev log (different audience, not a duplicate). FILE_03's check keeps them in sync so
  they never silently disagree.
- **One "release" = a version bump + an approved admin note + founder sign-off.** Not every merge to
  `main` is a release. Preserves the existing deploy behaviour (demo auto-deploys on push) — a
  "release" is the intentional, documented event on top.

## Out of scope (do NOT do here)

- No new versioning scheme (SemVer already in use). No change to how the demo deploys.
- No backend model/API/admin for releases. No customer-editable notes.
- No auto-publishing a release just because a PR merged (AI may *draft*; a human approves).
- No roadmap/PM system inside the repo (Linear stays the product-work source of truth; notes just
  *reference* Linear IDs / PR numbers).

## Before building — read these first

`apps/web/src/help/types.ts` (the `L` model + why prose lives in TS) · `SystemPage.tsx` +
`api/system.ts` (the version line to hang "What's New" beside) · `Docs/RUNBOOK.md` §Release ·
this repo's `CHANGELOG.md` + `VERSION` · `conductor-brand` + `erp-frontend` skills (any UI session).
