# Conductor ERP web — before you say "done"

Run from `apps/web`: `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`, and `npm run test`
(Vitest — pure-logic units only: `lib/money.ts`, `lib/customFields.ts`, `lib/workflow.ts` so far;
add a test alongside any new pure-logic module you write). Full mechanical brand gate:
`python scripts/gates/gate03.py` (repo root). A green gate means *not mechanically off-brand* —
still run the `conductor-brand` brand-feel checklist (the judgment rules a gate can't see). Green
gate **and** passed checklist = actually done.
