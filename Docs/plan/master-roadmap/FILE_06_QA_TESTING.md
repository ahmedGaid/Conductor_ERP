# D6 — Quality Assurance & Testing

> Existing owners: AI eval harness + golden ar/en dataset → `ai-reliability-roadmap` FILE_01
> (queue 6); i18n parity + brand gates already exist (gate00–14, parity script). This domain
> adds the classical-software half: coverage floor, factories, golden money scenarios,
> browser E2E, and seed data. **There is no JS unit-test runner today** — that stays true
> unless D6.P2.T1's decision changes it.

---

## Phase D6.P1 — Backend test floor

### D6.P1.T1 — Coverage baseline + ratchet gate
**Status:** todo · **Model:** Haiku — DECISION-GATED (dev-dep: coverage/pytest-cov)
**Objective:** measure per-app line coverage; commit `scripts/gates/coverage_floor.json` with current numbers; gate fails any app dropping below its recorded floor (ratchet up only, never down).
**Rationale:** floors beat targets — no bikeshedding a magic %, no regression by neglect.
**Prerequisites:** DECISIONS entry (dev-only dep).
**Steps:** 1. Entry. 2. Run `pytest --cov=erp` once; record per-app floors. 3. `scripts/gates/gate19.py` compares run vs floors, updates floors upward automatically in-place when exceeded (commit shows the ratchet). 4. Register warn-level first session, fail-level after one week.
**Affected files:** `pyproject.toml`, `scripts/gates/gate19.py` (new), `coverage_floor.json` (new), `_run.py`.
**Acceptance criteria:** gate green; artificially deleting a test file makes it fail naming the app.
**Testing:** run gate; plant-test.
**DoD:** gates green, status flipped.

### D6.P1.T2 — Factory conventions + shared scenario builders
**Status:** todo · **Model:** Sonnet
**Objective:** one documented factory/builder convention; shared business-scenario builders in `erp/core/tests/scenarios.py`: `company_with_openings()`, `sale_to_cash_cycle()`, `purchase_to_payment_cycle()` — each returns typed handles to every created record.
**Rationale:** cross-module tests (costing, close, VAT) all need "a company with real books"; today each test hand-rolls it — slow to write, drift-prone, weak-agent hostile.
**Prerequisites:** D1.P1.T4 (opening balances service exists to build on).
**Steps:** 1. Survey current test fixtures per app (codegraph). 2. Write the three builders through SERVICE layers only (never `Model.objects.create` for documents — tests must exercise real paths). 3. Convert 3 existing heavyweight tests to prove ergonomics. 4. Document in `Docs/patterns/testing.md` (new).
**Architecture decisions:** builders call services (real invariants) — slower but true; raw-ORM fixtures allowed only for reference data.
**Affected files:** `erp/core/tests/scenarios.py` (new), `Docs/patterns/testing.md` (new), 3 converted tests.
**Acceptance criteria:** the three builders produce balanced books (`verify_ledger` clean on the scenario DB).
**Testing:** `pytest erp/core -k scenarios` + converted tests green.
**DoD:** gates green, status flipped.

### D6.P1.T3 — Golden money scenarios (the trust suite)
**Status:** todo · **Model:** Opus (author numbers) then Sonnet
**Objective:** a `erp/core/tests/golden/` suite of end-to-end business scenarios with EXACT expected numbers hand-computed in the test docstring: sale with VAT rounding edge, partial payment allocation, credit note reversal, purchase with landed cost, month of activity → trial balance totals, VAT return boxes.
**Rationale:** "correct money" is value #1 and the ARP flagship depends on it; golden numbers catch subtle rounding/sign regressions no unit test sees.
**Prerequisites:** D6.P1.T2, D1.P2.T1 (costing — the landed-cost scenario waits for it; land the rest first).
**Steps:** 1. Author 6 scenarios on paper (docstring shows the arithmetic, minor units). 2. Implement via scenario builders. 3. Assert exact integers — no `approx`. 4. Register as its own pytest marker `golden` run in every gate pass.
**Architecture decisions:** expected values are literals in tests, never computed by the code under test.
**Affected files:** `erp/core/tests/golden/` (new package), testing pattern doc.
**Acceptance criteria:** all six green with hand-verified literals; a deliberate off-by-one piaster in any assertion fails.
**Testing:** `pytest -m golden`.
**DoD:** gates green, status flipped.

## Phase D6.P2 — Frontend & end-to-end

### D6.P2.T1 — E2E framework decision + smoke pack
**Status:** todo · **Model:** Opus (decision) then Sonnet — DECISION-GATED (dev-dep: Playwright)
**Objective:** DECISIONS entry adopting Playwright (dev-only) or explicitly deferring; if adopted: a 6-journey smoke pack — login, create+post invoice, receive payment, inventory receipt, assistant ask (read-only), language/theme switch — runnable headless against the dev stack, in BOTH ar and en.
**Rationale:** gates catch mechanical drift; only a browser catches "the app doesn't actually work". Six journeys ≈ 80% of demo risk.
**Prerequisites:** DECISIONS entry; dev stack boot documented (see D7.P1.T1).
**Steps:** 1. Entry (include the "no JS unit runner" status quo — Playwright covers the integration layer instead; component-level stays tsc+catalog). 2. Install dev-only. 3. `apps/web/e2e/` with fixture login + the six specs, each parameterized `ar`/`en`. 4. Seed-data hook (D6.P2.T3). 5. npm script + CONTRIBUTING; CI wiring lands with D7.P2.T1.
**Architecture decisions:** selectors via `data-testid` ONLY (add attributes as needed — they're free); no screenshot assertions yet (visual regression separately decided later).
**Affected files:** `DECISIONS.md`, `apps/web/e2e/` (new), touched components (`data-testid`), `apps/web/package.json`.
**Acceptance criteria:** 12 runs (6×2 languages) green locally from one command.
**Testing:** the suite itself; run twice to confirm no flake.
**DoD:** gates green, status flipped, `erp-status` updated.

### D6.P2.T2 — RTL/i18n automated sweep
**Status:** todo · **Model:** Sonnet
**Objective:** an E2E spec that walks every route from the route registry, in Arabic, asserting: no horizontal overflow, no untranslated-key leakage (regex for `\w+\.\w+\.` visible text), `dir="rtl"` integrity, and console-error-free render.
**Rationale:** Arabic-first is the brand; automated coverage keeps it true fleet-wide as pages multiply.
**Prerequisites:** D6.P2.T1.
**Steps:** 1. Export a route manifest from `App.tsx` (or generate from the router config). 2. Spec iterates routes with seeded data. 3. Failures print route + screenshot to a local artifacts dir.
**Affected files:** `apps/web/e2e/rtl-sweep.spec.ts` (new), route manifest export.
**Acceptance criteria:** sweep green on all routes; planted hardcoded string caught.
**Testing:** run sweep; plant-test.
**DoD:** gates green, status flipped.

### D6.P2.T3 — Deterministic seed dataset
**Status:** todo · **Model:** Sonnet
**Objective:** ONE deterministic demo-company seed path building the same realistic Egyptian trading company every time (fixed slugs/dates/amounts): 2 users with distinct roles, 20 products, 10 partners, 1 month of documents, opening balances — idempotent (re-run = no-op). NOTE: seeds already exist (`manage.py seed_identity`, `seed_accounting`, `scripts/seed_demo.py` — see erp-status env facts) — this task CONSOLIDATES/EXTENDS them, it does not start over.
**Rationale:** E2E, demos, screenshots, and the owner's own testing all need one known company; today the seed set is split and its determinism/idempotency is unverified.
**Prerequisites:** D6.P1.T2 (reuses scenario builders). Read the three existing seed entry points first.
**Steps:** 1. Audit existing seeds for determinism + idempotency; fold gaps into one entry point (management command wrapping the rest). 2. Extend with the document month via scenario builders, Arabic names from the brand lexicon. 3. Idempotency via a seed-marker setting row. 4. Document in CONTRIBUTING + Owner Manual.
**Architecture decisions:** goes through services (real books, `verify_ledger`-clean); never available when `DEBUG=False` unless `--force`.
**Affected files:** `erp/setup/management/commands/seed_demo.py` (new), CONTRIBUTING.
**Acceptance criteria:** fresh DB + seed = working company passing `verify_ledger` + `verify_sequences`; second run changes nothing.
**Testing:** pytest invoking the command twice, diffing row counts.
**DoD:** gates green, status flipped.

## Phase D6.P3 — Release discipline

### D6.P3.T1 — Release smoke checklist codified
**Status:** todo · **Model:** Haiku
**Objective:** `Docs/runbooks/release-checklist.md`: full gate run (`gate:all`), pytest, parity, tsc, E2E smoke pack, seed-demo boot, plus the 5-minute manual sweep list (both languages, both themes) — every merge-checkpoint from EXECUTION_ORDER points here.
**Rationale:** the checklist exists in fragments across skills/docs; one canonical page removes drift.
**Prerequisites:** D6.P2.T1.
**Steps:** consolidate; link from EXECUTION_ORDER merge section + CONTRIBUTING.
**Affected files:** `Docs/runbooks/release-checklist.md` (new), EXECUTION_ORDER (one link line).
**Acceptance criteria:** one page, every command copy-pasteable.
**Testing:** run it once end-to-end; fix anything stale.
**DoD:** committed, status flipped.
