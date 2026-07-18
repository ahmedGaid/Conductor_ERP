# FILE_03 — English product-vocabulary canon (done 2026-07-19)

## Scope
Extend the lexicon moat (Identity System §6, today Arabic-first) to English product nouns: prefer
human words over "Master Data / Utilities / Configuration" where a human word fits. One canonical
English word per concept, registered before use; brand-doc task first, build second.

## What shipped
- **Brand doc** — `Docs/Brand/Conductor_Visual_Identity_System.md` §6.4 (new), mirroring §6.1's
  table + governance structure: 9 concepts registered with their canonical English noun + what to
  avoid (Assistant, Assistant health, Knowledge base, Activity, Developers, Custom fields, Saved
  view, System confidence, Webhook). Three CPO-named concepts (Insights, Workspace, "the daily
  brief's name") are explicitly marked **reserved, not registered** — none has a shipped surface
  yet, and the governance rule is to register *before* a feature ships, not ahead of it.
- **Audit finding:** a grep across `en.json` for generic enterprise nouns ("Master Data",
  "Utilities", "Configuration", etc.) found nothing — the app was already ~clean, confirming the
  arp-roadmap note that most of the CPO review was already shipped practice. One real drift found:
  **"AI ops"** (nav label + page title) read as internal-tooling jargon, not a human word, and its
  Arabic counterpart **"عمليات الذكاء الاصطناعي"** additionally violated the *existing* §6.1 rule
  that "AI" alone never appears in Arabic copy (the assistant surface is always المساعد الذكي).
- **Rename** (light pass, 3 files): `apps/web/src/i18n/locales/en.json`
  (`nav.opsAdmin` + `ops.title`: "AI ops" → "Assistant health"), `ar.json` (same two keys:
  "عمليات الذكاء الاصطناعي" → "صحة المساعد", now lexicon-compliant), and
  `apps/web/src/help/content/platform.ts` (`opsGuide.title`, same rename, both languages — the
  User Guide entry for this page).

## Verified
- `grep -rn "AI ops"` across `apps/web/src` — zero remaining references after the rename.
- `node scripts/check-i18n-parity.mjs` — 2033 keys, ar/en parity green (rename only, no key
  count change).
- `npx tsc -b` — clean.
- `python scripts/gates/gate03.py` — green.
- **Live (rung 3):** same temp-local-Django-on-:8010 pattern as FILE_01/FILE_02. Navigated to
  `/assistant/ops` — page title and sidebar nav link both render "Assistant health"; confirmed via
  accessibility tree, not just page text. Arabic string verified via the automated parity gate
  (same limitation noted in FILE_01/02 — in-browser language toggle doesn't reflect a localStorage
  change while logged in, a pre-existing user-preference precedence unrelated to this change).
  Reverted `vite.config.ts`, killed the temp Django process after.

## Deviations
- No route/URL changes — `/assistant/ops` keeps its path; only the human-facing label changed
  ("light rename", not a restructure).
- Did not invent names for Insights/Workspace/daily-brief. This is deliberate, not an omission —
  see the brand-doc entry's "Reserved" note.

**Track P (`Docs/plan/craft-trust-polish/`) is now 3/3 — complete.**
