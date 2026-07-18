# FILE_04 — Frontend unit tests (Vitest)

## Finding
`apps/web` has NO JS/TS unit-test runner (no vitest/jest/testing-library in `package.json`) — only
Playwright E2E. Critical pure-logic units (money format/parse, form validation, workflow-canvas
state) have no fast unit coverage; a regression only surfaces in a slow E2E run or in production.

## Tasks
- [ ] Add Vitest + @testing-library (dev deps; DECISIONS entry — new tooling). Vite already present,
      so config is light.
- [ ] Add `npm run test` (+ `test:watch`) to `apps/web/package.json`.
- [ ] Cover the highest-risk pure logic first: `lib/money.ts` (minor-unit format/parse, rounding,
      Arabic digits), form validation helpers, workflow-canvas state reducers, i18n key resolution.
- [ ] Wire `npm run test` into the CI `web` job (from `pre-handover-hardening/FILE_02`).

## Watch
- Unit-test the LOGIC, not the framework. Money and RTL/Arabic-digit edge cases are the payoff.
- Keep E2E as the integration layer — Vitest is for fast pure-logic feedback, not duplicating E2E.

## Done when
`npm run test` runs a green Vitest suite covering money + validation + canvas-state; CI runs it;
a deliberate money-rounding bug turns it red.

## How to test
- `cd apps/web && npm run test` → suite passes.
- Break a `money.ts` rounding case → the test fails.
