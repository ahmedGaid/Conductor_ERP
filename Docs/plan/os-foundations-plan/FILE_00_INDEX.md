# Phase W+ — Agentic OS Foundations (L0–L2) — Master Index

## Project Goal

Build the three bottom layers of the Agentic OS (`Docs/ARP_DEEP_VISION.md` §2) that Phase A
(smart-import), A2 (consultant), and B (month-close) all ride on:

- **L0 — Action Graph v2**: every assistant write-action declares, as data, its `requires` /
  `effects` / `invariants` / `compensation` / `risk` / `idempotency_key`.
- **L1 — Verifier**: deterministic invariant packs run after EVERY agent write; failure →
  automatic compensation + an honest report card. "The model narrates; it never computes."
- **L2 — Simulation**: dry-run a multi-step plan inside one rolled-back transaction → one
  **diff card** ("This will create 3 customers, 1 price list, 14 orders; receivables +42,300
  EGP. Approve?").

**The claim this phase buys:** *"See tomorrow's books before you post them."*

## Approach decisions (founder-approved 2026-07-12)

| Decision | Choice |
|---|---|
| Simulation fidelity | **Hybrid**: real `execute()` inside `transaction.atomic` that always rolls back; a sim-mode flag stubs external side effects (notifications, ETA submission). Doc sequences are SELECT-max+1 (`sales/services/orders.py::_next_number` et al.) so rollback restores them — no burn, no stub needed. |
| Retrofit breadth | **Framework + representative slice**: full L0 metadata on 4 archetype actions; the other 13 get safe defaults now and a mechanical (Haiku-fit) follow-up later. |
| Registry home | **Assistant-side**: extend the existing `Action` dataclass + registration in `erp/assistant`. Module `contracts.py` signatures untouched. The true contract-decorator ("every new module agent-operable on day one") is documented as a follow-up path in FILE_01, not built here. |

## We extend what exists — never rebuild

| Capability | Where it lives today |
|---|---|
| Write-action registry (17 actions, propose→confirm) | `erp/assistant/services/actions.py` — `Action` dataclass L1254, `ACTIONS` L1266, `build()` L1446, `execute()` L1463 |
| Confirm flow (single-use proposal card in `Message.meta`) | `erp/assistant/api/views.py` L302–342 |
| Dry-run precedent (preview/execute split) | `erp/assistant/services/imports.py::preview/execute` |
| Idempotency-key precedent | `erp/workflow/` engine wraps external-write nodes |
| Invariant data sources | `erp/accounting/services/reports.py::trial_balance` L46; `erp/inventory/services/reports.py::stock_on_hand` L30; per-module `_next_number` (max+1 style) |
| Audit | `erp.audit.services.record(...)` — ONLY entry point |
| Agent loop + planner prompt | `erp/assistant/services/agent.py`; `actions.catalog_text()` L1437 |

## DEDUPE GUARDS — already built elsewhere, DO NOT REBUILD

| Concern | Lives in | Status |
|---|---|---|
| Eval harness + golden dataset (ar/en) | ai-reliability FILE_01 (T1.x) | **DONE** — W+'s old "eval harness lands here" line is superseded |
| Model routing + admission rule (G3) | ai-reliability FILE_02 | **DONE** |
| Answer self-verification / groundedness | ai-reliability FILE_05 T5.8 | queued there — this phase's L1 checks **write invariants**, a different concern |
| Planner (graph traversal → ordered plan) | L3, a later phase (arp-roadmap) | OUT OF SCOPE — FILE_04 simulates a *given* step list; it does not derive one |
| Company Brain / Autonomy Ladder (L4/L5) | Phase B2 | OUT OF SCOPE |

## The 5 session files (ONE FILE = ONE SESSION)

| File | Layer | Delivers |
|---|---|---|
| FILE_01 | L0 | `Action` schema v2 (declared semantics) + registration validation + 4-archetype retrofit + safe defaults on the rest |
| FILE_02 | L1 | Verifier framework + 6 invariant packs, unit-tested standalone |
| FILE_03 | L1 | Wire verifier after `execute()`; auto-compensation; idempotent confirms; verdicts audited |
| FILE_04 | L2 | Simulation engine: sim-mode stubs + rolled-back atomic over a step list → structured diff |
| FILE_05 | L2 + accept | `/api/assistant/simulate` + web diff card (ar/en, designed states) + phase acceptance |

Execution protocol (same as ai-reliability): new session → paste this FILE_00 + the next `FILE_NN`
without `_done` → do its tasks in order → run each Accept block → commit → check the boxes → rename
the file `_done` → fresh session. A `_done` file is never reopened.

## Task format (identical in every file)

Every task carries: **Goal** (one sentence, testable) · **Prereq** · **Files** (exact paths) ·
**Steps** (numbered, deterministic) · **Accept** (objective pass/fail + test command) · **Output**.

## Hard rules — inherited, non-negotiable, every task

1. **Tool-use, never free-text-to-SQL.** Every data access runs as `actor` = request user; RBAC +
   scope + audit always hold.
2. **Writes are human-in-the-loop.** `post`/`destructive` risk NEVER auto-executes (deep vision §8).
3. **Additive.** Extend `actions.py`, `views.py`, `api/urls.py` — existing endpoints keep working.
4. **No new dependencies** without asking. Every task here works with the current stack.
5. **Frontend:** tokens only, logical CSS only, ar+en parity, designed empty/error/loading states,
   settled motion, no new npm deps.
6. **Arabic-first.** Diff card + report card copy exists in BOTH `ar.json`/`en.json`; Arabic terms
   follow the Identity System §6 lexicon (recall `conductor-brand` before writing user-facing copy).
7. **Gates before "done":** `pytest erp/assistant` (plus touched modules); from `apps/web`:
   `node scripts/check-i18n-parity.mjs` + `npx tsc -b`; repo root `python scripts/gates/gate03.py`
   when UI touched. Full suite `scripts/gates/_run.py all` at FILE_05.
8. **`Docs/ARP_STRATEGY.md` governs scope.** Conflict → stop and flag.

## Never touch

- `erp/audit/models.py` (append-only; use `erp.audit.services.record`)
- `apps/web/src/styles/tokens.css` (no new raw hex)
- `apps/web/src/lib/money.ts`
- Existing module `contracts.py` signatures
- Other apps' migrations

## Decision points (ask before the task that needs them)

- **FILE_04**: where the sim-mode flag lives — `contextvars.ContextVar` in a new
  `erp/assistant/services/simulation.py` (recommended; thread-safe, no settings sprawl) vs a
  request attribute. Proposed in FILE_04 T4.1; approve there.
- **FILE_05**: whether the diff card endpoint is exposed to the agent loop in this phase (so the
  model can *offer* a simulation) or stays UI-triggered only. Default: UI/confirm-flow triggered
  only; the agent-loop hookup belongs to L3 planning.

*Generated 2026-07-12. Grounded in erp/assistant as of commit 4c3be91.*
