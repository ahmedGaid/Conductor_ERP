# FILE_04 — Frontend unit tests (Vitest)

## Finding
`apps/web` has NO JS/TS unit-test runner (no vitest/jest/testing-library in `package.json`) — only
Playwright E2E. Critical pure-logic units (money format/parse, form validation, workflow-canvas
state) have no fast unit coverage; a regression only surfaces in a slow E2E run or in production.

## Tasks
- [x] Add Vitest + @testing-library (dev deps; DECISIONS entry — new tooling). Vite already present,
      so config is light.
- [x] Add `npm run test` (+ `test:watch`) to `apps/web/package.json`.
- [x] Cover the highest-risk pure logic first: `lib/money.ts` (minor-unit format/parse, rounding,
      Arabic digits), form validation helpers, workflow-canvas state reducers, i18n key resolution.
- [x] Wire `npm run test` into the CI `web` job (from `pre-handover-hardening/FILE_02`).

## Watch
- Unit-test the LOGIC, not the framework. Money and RTL/Arabic-digit edge cases are the payoff.
- Keep E2E as the integration layer — Vitest is for fast pure-logic feedback, not duplicating E2E.

## Done when
`npm run test` runs a green Vitest suite covering money + validation + canvas-state; CI runs it;
a deliberate money-rounding bug turns it red.

## How to test
- `cd apps/web && npm run test` → suite passes.
- Break a `money.ts` rounding case → the test fails.

## Closed 2026-07-19 (A) — see DECISIONS.md for the @testing-library / target-substitution call
Only `vitest` added (not `@testing-library/react`) — the three chosen targets are pure TS/TS
functions, no DOM rendering needed; adding an unused dependency would have been scope creep past
what the founder approved. `npm run test` → 39 passed, 0 failed. Wired into `.github/workflows/
ci.yml`'s `web` job as a new `Unit tests` step, before the i18n/typecheck/build steps (fail fast).
