# SESSION 1 — Release-note data model + seed + governance rule
# Files: apps/web/src/releases/content.ts (new), apps/web/src/releases/types.ts (new),
#        VERSION, CHANGELOG.md, Docs/RUNBOOK.md, DECISIONS.md
# Model: Sonnet (clear spec, no ambiguity). Say so and wait for /model before building on Opus.

This session builds the **data foundation and the written rule** — no UI yet (FILE_02 renders it).
Reuse the version backbone that already exists; do not invent a new one.

---

## Before You Start (read, do not write yet)

1. `apps/web/src/help/types.ts` — study `type L = { en: string; ar: string }` and the top comment
   explaining *why* long-form prose lives in TS modules, not the parity-checked i18n JSON. The
   release model copies this exactly.
2. `apps/web/src/help/content/glossary.ts` — a real example of `L`-typed bilingual data.
3. Root `VERSION` (`1.0.0`) and `CHANGELOG.md` (top section `## v1.1.0 — 2026-07-20`). Note the
   drift: the file was never bumped when v1.1.0 shipped (twenty-harvest). Confirm with the founder
   that **1.1.0 is the current shipped version** before bumping.
4. `Docs/RUNBOOK.md` §"Release (maintainer, before shipping a new version)" — you will extend it.

---

## Task A — the types

New `apps/web/src/releases/types.ts`, reusing `L` from help:

```ts
import type { L } from "../help/types";

export type ReleaseStatus = "candidate" | "released";
export type ChangeKind = "added" | "fixed" | "changed";

/** One line in the summary list — a single user-facing change, plain words. */
export interface ReleaseChange {
  kind: ChangeKind;
  summary: L;
  featureId?: string; // optional link to a ReleaseFeature deep-dive below
}

/** A numbered, deterministic test an Admin can run, and what they should see. */
export interface ValidationScenario {
  name: L;
  steps: L[];     // numbered in the UI — author as ordered steps
  expected: L[];  // what proves it worked
}

/** Deep-dive for a notable NEW feature. Answers: what is it, why does it matter, how to test. */
export interface ReleaseFeature {
  id: string;         // stable slug, unique within its release
  title: L;
  whatItIs: L;
  whyItMatters: L;    // value to the USER and to the BUSINESS — one short paragraph
  validation: ValidationScenario;
}

/** One release. `version` mirrors VERSION / CHANGELOG (no leading "v"). Newest first in the array. */
export interface Release {
  version: string;
  date: string;       // ISO yyyy-mm-dd
  status: ReleaseStatus;
  headline: L;
  changes: ReleaseChange[];
  features?: ReleaseFeature[];
  work?: { issues?: string[]; prs?: string[] };
  technical?: L;
}
```

## Task B — the data + seed with the two real releases

New `apps/web/src/releases/content.ts`:

```ts
import type { Release } from "./types";
export const RELEASES: Release[] = [ /* newest first */ ];
```

Seed **two real entries** from the existing `CHANGELOG.md`, translated to admin-plain **Arabic +
English** (Arabic-first — this is the primary audience). Rewrite the terse dev bullets into
user-visible language:

- **v1.1.0 (2026-07-20, released)** — headline + Added/Fixed/Changed from the CHANGELOG v1.1.0
  bullets, phrased for an Admin. Include **at least one full `ReleaseFeature` deep-dive** so FILE_02
  has real content to render — recommended: **Saved views** (list-page filter/sort presets) or the
  **⌘K command palette**. Its `validation` must be a real, numbered, deterministic scenario a
  founder can actually run in the app, with concrete expected results (see the example below).
- **v1.0.0 (2026-07-16, released)** — headline + a short Added summary of the shipped core (five
  modules + accounting + VAT + ETA e-invoicing + RBAC). No deep-dive needed for the historical base.

Example of the quality bar for one feature deep-dive (author both languages — English shown):

```
title:        Saved views
whatItIs:     A saved view remembers the filters, sorting, and columns you set on any list, so you
              can reopen the same slice in one click instead of setting it up again.
whyItMatters: Staff stop re-filtering the same list every morning, and everyone opens the business
              on the same, agreed view — fewer mistakes, faster daily work.
validation.name:  Save and reopen a view on the Customers list
validation.steps: 1. Open Sales → Customers.
                  2. Filter to one city and sort by newest.
                  3. Click "Save view", name it, confirm.
                  4. Leave the page, then reopen Customers and pick your saved view.
validation.expected: - Your saved view appears in the views list by the name you gave it.
                     - Choosing it restores the exact filter, sort, and columns.
                     - No other list is affected.
```

Keep prose short. An Admin should understand any single release in under two minutes.

## Task C — fix the version drift (single source of truth)

Once the founder confirms 1.1.0 is current:

- `VERSION` → `1.1.0` (single line, no trailing newle beyond the existing convention).
- Leave `CHANGELOG.md` v1.1.0 section as-is (it already exists); it stays the internal dev log.
- The `content.ts` top entry `version: "1.1.0"` must match both.

## Task D — write the governance rule

Extend `Docs/RUNBOOK.md` §Release with a short **"What counts as a release"** subsection:

- **SemVer intent:** PATCH = bug fixes / safe internal improvements · MINOR = new backward-compatible
  user-facing features · MAJOR = breaking change or major product milestone.
- **A release is an intentional event, not every merge.** Merges to `main` keep `main` releasable
  and auto-update the demo (unchanged). A *release* = bump `VERSION` + write & **founder-approve** an
  admin release note in `releases/content.ts` + add the `CHANGELOG.md` section + `git tag vX.Y.Z`.
- Point to `Docs/plan/admin-release-notes/` for the note format.

Record the same three decisions from `FILE_00_INDEX.md` ("Decisions taken") in `DECISIONS.md` under a
new `release-notes:` entry, so they are not re-litigated later.

---

## Smoke Test

- [ ] `apps/web`: `npx tsc -b` green (the new types compile; `content.ts` satisfies `Release[]`)
- [ ] `node scripts/check-i18n-parity.mjs` green (no new **prose** in the locale JSON — prose is in
      `content.ts`; only FILE_02 adds the short chrome-label keys)
- [ ] `python scripts/gates/gate03.py` green
- [ ] `VERSION`, `CHANGELOG.md` top section, and `RELEASES[0].version` all read `1.1.0`
- [ ] Every `L` field in `content.ts` has BOTH `ar` and `en` filled (no empty strings)
- [ ] RUNBOOK "What counts as a release" reads as plain, correct guidance; `DECISIONS.md` updated

## After This Session

```
Smoke passed? → Rename this file with _done. Update erp-status (position + next = FILE_02).
Commit (conventional, reference this plan). → Open FILE_02 in a FRESH session.
NEXT: FILE_02 renders this data as the in-app "What's New" (Settings + Help). Model: Opus (UI/brand).
```
