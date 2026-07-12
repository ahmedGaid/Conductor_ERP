# FILE_05 — L2: Diff card (API + web) + phase acceptance

> ONE SESSION. Prereq: FILE_01–04 `_done`. This file closes Phase W+.

## Why

The simulation diff becomes the product moment: ONE card — "This will create 3 customers,
1 price list, 14 orders; receivables +42,300 EGP. Approve?" — before anything real happens.
Phase A's import preview and Phase B's month-close preview will render this same card.

## Scope guard

Per FILE_00 decision point 2 (default): the endpoint is UI/confirm-flow triggered. The agent loop
does NOT get a `simulate` tool in this phase — that hookup belongs to L3 planning. The card is
proven here via a direct API call + a dev-visible surface, so the phase is demonstrable without
waiting for the planner.

## Tasks

### [x] T5.1 — `POST /api/assistant/simulate`

- **Goal:** an authenticated endpoint takes `{steps: [{action, args}]}` and returns the FILE_04
  diff envelope.
- **Files:** `erp/assistant/api/views.py` (new view, follow `_envelope` + permission patterns);
  `erp/assistant/api/urls.py`; `erp/assistant/tests/test_api.py` (or the existing API test file).
- **Steps:**
  1. Validate: ≤ 10 steps; every `action` exists in `ACTIONS`; feature-gated by
     `client.enabled()` like the other assistant views? NO — simulation needs no LLM; gate only
     on `IsAuthenticated`. Say so in a comment.
  2. RBAC holds inside: `actions.build/execute` already run as the actor (nothing to add — the
     simulation refuses exactly what a real run refuses; test it).
  3. Return the diff verbatim; 400 on unknown action or >10 steps.
- **Accept:** API tests: happy 2-step path; unknown action → 400; an actor without create rights
  → the step fails with the existing refusal, `ok: false`, nothing written.
- **Output:** simulation reachable over HTTP.

### [x] T5.2 — The diff card component (ar/en, designed states)

- **Goal:** one web component renders the diff envelope; brand-true in both languages.
- **Files:** NEW `apps/web/src/assistant/SimulationDiffCard.tsx` (+ its CSS module); wire it into
  the assistant panel as a card variant the way proposal cards render; `ar.json` + `en.json`.
- **Steps:**
  1. Recall `conductor-brand` + `erp-frontend` FIRST (both apply — brand copy + implementation
     primitives).
  2. Layout: summary sentence built from `creates` (localized plurals) → money deltas via
     `lib/money.ts` formatting at the edge → per-step list with ✓/⚠ + verifier verdicts → the
     failing step (if any) shown with the blame-free message + "nothing was written" line.
  3. States: loading (settled skeleton), error, empty (a plan with zero steps never renders a
     bare card). Logical CSS only; token colors only; color always pairs with a word.
  4. Arabic copy: one canonical word per concept — check Identity System §6 before inventing
     terms (e.g. محاكاة vs معاينة — pick per lexicon, add there if missing).
- **Accept:** from `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc -b`; repo root
  `python scripts/gates/gate03.py` — all green. Manual: card renders RTL-first, reads identically
  in EN.
- **Output:** the reusable diff card — Phase A/B's preview surface.

### [x] T5.3 — Demo wiring (how a user reaches it today)

- **Goal:** one real path to trigger a simulation without the L3 planner.
- **Files:** assistant panel (`apps/web/src/assistant/`); i18n files.
- **Steps:** on a multi-action proposal message — or, simplest, on any pending proposal card —
  add a quiet secondary "معاينة الأثر" / "Preview impact" affordance that calls
  `/api/assistant/simulate` with that one proposal's step and renders the diff card above the
  confirm button. One step is a degenerate plan — the wiring is identical and honest.
- **Accept:** manual run (`run-dev.ps1`, admin login): ask the assistant for a sales-order draft
  → card appears → "Preview impact" → diff card shows the would-be order + receivables delta →
  confirm still works as before. Web gates green.
- **Output:** the demoable moment; "see it before it happens" in the product.

### [x] T5.4 — Phase acceptance

- **Goal:** Phase W+ provably done.
- **Steps:**
  1. Full suite: `.\.venv\Scripts\python.exe scripts\gates\_run.py all` (00–15) green.
  2. `pytest erp/assistant` (and touched modules) green.
  3. Web gates (parity, tsc, gate03) green.
  4. Scripted check: simulate a 3-step plan (customer → order → journal draft) via the API;
     assert diff correctness and zero persistence; then run the same plan for real via confirms;
     assert the diff predicted the outcome (counts + money deltas match). This script lives in
     `erp/assistant/tests/test_simulation.py` as the phase's exit test.
  5. Brand-feel checklist (`conductor-brand`) on the diff card — gate03 green ≠ on-brand.
  6. Log in `DECISIONS.md`: simulation layer (hybrid, ContextVar), action-graph schema v2,
     rollback-as-compensation posture, the 13-action metadata fan-out as a Haiku follow-up.
  7. Update `EXECUTION_ORDER.md` row 7 status; update `erp-status` (position → pos 8
     smart-import, NOTE: FILE_13 preview UI should consume the diff card); rename this file
     `_done`.
- **Accept:** every item above checked; all gates green in one run.
- **Output:** Phase W+ closed. Claim earned: **"See tomorrow's books before you post them."**

## After this session

Commit (`feat(assistant): os-foundations L2 — diff card + phase W+ acceptance`) → fresh session →
queue position 8: `Docs/plan/smart-import-plan/FILE_01`.
