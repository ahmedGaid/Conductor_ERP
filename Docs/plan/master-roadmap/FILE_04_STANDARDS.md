# D4 — Implementation Framework & Coding Standards

> Make the "right way" mechanical so ANY agent (or human) produces uniform code. Cheapest
> domain, highest leverage — do P1 at the first natural queue gap. Net-new (no existing plan
> owns this).

---

## Phase D4.P1 — The written floor

### D4.P1.T1 — CONTRIBUTING.md + backend pattern doc
**Status:** todo · **Model:** Sonnet
**Objective:** `CONTRIBUTING.md` (≤150 lines): branch naming, conventional commits, session protocol pointer, gate list; plus `Docs/patterns/backend.md`: the canonical service/repository/contract/api layering with ONE fully-worked example (copy-paste template) including error handling, audit call, permission check, i18n error message.
**Rationale:** weak agents copy patterns; give them the golden one. Today the pattern lives only in existing code — implicit.
**Prerequisites:** D2.P1.T2 (ARCHITECTURE.md) recommended, not blocking.
**Steps:** 1. Extract the best existing service (pick from `erp/accounting/services/`, confirmed via codegraph) as the exemplar. 2. Annotate every layer decision inline. 3. Write both docs; link from CLAUDE.md map.
**Architecture decisions:** the exemplar is normative — divergence needs a reason in PR text.
**Affected files:** `CONTRIBUTING.md` (new), `Docs/patterns/backend.md` (new), `CLAUDE.md` (one line).
**Acceptance criteria:** a new module CRUD slice can be written from the pattern doc alone without reading other apps.
**Testing:** n/a (docs).
**DoD:** committed, status flipped.

### D4.P1.T2 — Frontend pattern doc
**Status:** todo · **Model:** Sonnet
**Objective:** `Docs/patterns/frontend.md`: canonical page skeleton (header bar, table kit, meta columns), data-fetch hook pattern, optimistic-update + toast + undo pattern, form pattern with validation + blame-free errors, i18n key naming convention (`<area>.<page>.<element>`), file placement rules.
**Rationale:** same as T1 for `apps/web`; the `erp-frontend` skill carries discipline — this doc carries the copyable code.
**Prerequisites:** unified-ui FILE_02 done (it is).
**Steps:** extract exemplars from sales orders page (the reference kit), annotate, write doc, link from skill + CLAUDE.md.
**Affected files:** `Docs/patterns/frontend.md` (new), `CLAUDE.md`.
**Acceptance criteria:** a new list+detail page implementable from doc alone; key-naming rule stated once.
**Testing:** n/a.
**DoD:** committed, status flipped.

### D4.P1.T3 — Error envelope + i18n error catalog
**Status:** todo · **Model:** Sonnet
**Objective:** one documented API error shape (code, message key, params, field errors) verified across apps by a test; error message keys centralized per app in locales with the blame-free Arabic rule.
**Rationale:** assistants and UI both parse errors; drift here = broken UX and broken agent blocker-handling (§3 mechanic 5).
**Prerequisites:** none.
**Steps:** 1. codegraph: current error/exception classes (`erp/core/exceptions.py` exists). 2. Document the envelope in `Docs/patterns/backend.md` §errors. 3. Contract test in `erp/core/tests/` hitting a sample failing endpoint per app asserting the shape. 4. Catalog audit: every raised error code has ar+en keys.
**Architecture decisions:** error `code` is stable API; message text is not.
**Affected files:** pattern doc, `erp/core/tests/test_error_envelope.py` (new), stray non-conforming raisers (fix), locales.
**Acceptance criteria:** contract test green across all apps' sampled endpoints.
**Testing:** `pytest erp/core -k error_envelope` + full suite.
**DoD:** gates green, status flipped.

## Phase D4.P2 — Mechanical enforcement

### D4.P2.T1 — Python lint/format/type gate
**Status:** todo · **Model:** Haiku (config) — DECISION-GATED (new dev-deps: ruff, mypy)
**Objective:** ruff (lint+format) + mypy (gradual, per-app opt-in list) wired into the gate runner; zero-violation baseline via per-file ignores.
**Rationale:** style drift review costs > tool cost; type errors are the #1 weak-agent defect class.
**Prerequisites:** founder approval for dev-dependencies (DECISIONS entry — dev-only, not runtime).
**Steps:** 1. DECISIONS entry. 2. `pyproject.toml` config, line length matching current code. 3. `ruff check --add-noqa` style baseline (no mass reformat commit mixed with logic). 4. mypy strict on `erp/core` only initially; expansion list in config comment. 5. Gate registration.
**Architecture decisions:** format the tree ONCE in a dedicated commit; mypy expands app-by-app, never big-bang.
**Affected files:** `pyproject.toml`, `scripts/gates/_run.py`, one formatting commit.
**Acceptance criteria:** gates green; CI-equivalent local run documented in CONTRIBUTING.
**Testing:** run gate runner full.
**DoD:** gates green, status flipped.

### D4.P2.T2 — ESLint for apps/web
**Status:** todo · **Model:** Haiku — DECISION-GATED (dev-dep)
**Objective:** eslint flat config: typescript rules, react-hooks rules, custom rule set encoding brand law (no physical CSS props in style objects, no raw hex, no hardcoded user-facing strings — regex-based via `no-restricted-syntax`).
**Rationale:** moves brand law from post-hoc gate to editor-time signal.
**Prerequisites:** DECISIONS entry (dev-only).
**Steps:** 1. Entry. 2. Config + baseline via disable-comments audit (target zero — fix trivial, allowlist rest). 3. `npm run lint` + gate registration + CONTRIBUTING note.
**Affected files:** `apps/web/eslint.config.js` (new), `apps/web/package.json`, `_run.py`.
**Acceptance criteria:** lint green; planted hex/hardcoded-string violation caught.
**Testing:** run lint before/after plant.
**DoD:** gates green, status flipped.

### D4.P2.T3 — API type generation (backend → frontend)
**Status:** todo · **Model:** Opus (design) — DECISION-GATED if a generator dep is chosen
**Objective:** single source of truth for API shapes: generate TS types from backend serializers/contracts into `apps/web/src/api/types.gen.ts`; drift gate fails when regeneration changes the file.
**Rationale:** hand-maintained duplicate types are the standing source of silent breakage between Django and React.
**Prerequisites:** D4.P1.T3.
**Steps:** 1. Survey current `apps/web/src/api/` typing + backend contract shape (codegraph). 2. Design doc: options = DRF-spectacular→openapi-typescript vs bespoke generator over `contracts/` dataclasses; pick with DECISIONS entry. 3. Implement generator + npm script + gate. 4. Migrate 3 pilot endpoints' hand types to generated; fleet migration appended as follow-up tasks.
**Architecture decisions:** generated file committed (reviewable diffs), never hand-edited.
**Affected files:** generator script, `apps/web/src/api/types.gen.ts` (new), pilot api modules, `_run.py`.
**Acceptance criteria:** pilot endpoints typed end-to-end; changing a backend field without regenerating fails the gate.
**Testing:** tsc green; gate plant-test.
**DoD:** gates green, status flipped.

## Phase D4.P3 — Process

### D4.P3.T1 — ADR discipline formalized
**Status:** todo · **Model:** Haiku
**Objective:** `DECISIONS.md` gets a stated template header (context/decision/consequences/reversal-condition) + an index table at top; verify last 10 entries fit or annotate.
**Rationale:** DECISIONS is already the ADR log — make its shape explicit so agents write conforming entries.
**Prerequisites:** none.
**Steps:** add template + index; backfill index rows for existing entries (titles + dates only).
**Affected files:** `DECISIONS.md`.
**Acceptance criteria:** template present; index complete.
**Testing:** n/a.
**DoD:** committed, status flipped.

### D4.P3.T2 — PR checklist template
**Status:** todo · **Model:** Haiku
**Objective:** `.github/PULL_REQUEST_TEMPLATE.md` embedding the done-bar: gates run (paste output line), i18n parity, brand checklist (UI), permission story (AI features — ARP_STRATEGY §6.9), How-to-test block.
**Rationale:** the done-bar lives in skills/docs; PRs are where it's enforced socially.
**Prerequisites:** none.
**Steps:** write template mirroring EXECUTION_ORDER session protocol.
**Affected files:** `.github/PULL_REQUEST_TEMPLATE.md` (new).
**Acceptance criteria:** next PR renders the checklist.
**Testing:** n/a.
**DoD:** committed, status flipped.
