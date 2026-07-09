# MASTER ROADMAP — 13-domain engineering blueprint (index + execution contract)

> **What this is:** the full production blueprint for Conductor, organized into 13 domains,
> each broken into phases → small deterministic tasks executable by any AI coding agent
> (including weaker models) with zero hidden context.
> **What this is NOT:** a replacement for the live queue. `Docs/plan/EXECUTION_ORDER.md` stays
> the single answer to "what do I work on now". This roadmap is the **reservoir**: when the
> queue reaches a domain (or the founder promotes one), its tasks become the session scope.
> Created 2026-07-08. Owner-facing mirror: `Docs/OWNER_MANUAL.html`.

---

## Authority map (who wins on conflicts)

| Question | Owner |
|---|---|
| What do I build next, today | `EXECUTION_ORDER.md` queue |
| Category, scope, refuse-list | `Docs/ARP_STRATEGY.md` |
| Strategic phase order (W+, A, A2, B…) | `Docs/plan/arp-roadmap.md` |
| Company/business plan | `Docs/FOUNDER_PLAN.md` |
| Recorded decisions & reversals | `DECISIONS.md` |
| **Task-level engineering detail per domain** | **this folder** |

If a task here contradicts a doc above, the doc above wins — fix the task file in the same
commit you discover the drift.

## The 13 domains

| # | File | Domain | Overlap with existing plans |
|---|---|---|---|
| D1 | `FILE_01_CORE_ERP.md` | Core ERP Foundation | 03-costing, 09-eta, business-cycles harvest |
| D2 | `FILE_02_ARCHITECTURE.md` | Architecture & Scalability | 06-saas-multitenancy, os-foundations |
| D3 | `FILE_03_DESIGN_SYSTEM.md` | Design System & UX | unified-ui-plan, linear-polish-plan |
| D4 | `FILE_04_STANDARDS.md` | Implementation Framework & Coding Standards | — (net-new) |
| D5 | `FILE_05_SECURITY.md` | Security | 00-security-hardening |
| D6 | `FILE_06_QA_TESTING.md` | Quality Assurance & Testing | ai-reliability FILE_01 (evals) |
| D7 | `FILE_07_INFRA_DEVOPS.md` | Infrastructure & DevOps | 07-billing (provisioning half) |
| D8 | `FILE_08_DATA_PLATFORM.md` | Data Platform & Database | 05-reports-and-bi |
| D9 | `FILE_09_INTEGRATIONS.md` | Integrations & APIs | 09-eta, arp Phase E (WhatsApp) |
| D10 | `FILE_10_CUSTOMER_SUCCESS.md` | Customer Implementation & Success | smart-import-plan, arp Phase A2 |
| D11 | `FILE_11_MARKETPLACE.md` | Marketplace & Extensibility | arp Phase 5 (FOUNDER_PLAN §2) |
| D12 | `FILE_12_SAAS_OPS.md` | Product & SaaS Operations | 06 + 07 legacy plans |
| D13 | `FILE_13_DOCS_KNOWLEDGE.md` | Documentation & Knowledge Management | — (net-new) |

**Overlap rule:** where an existing plan folder already owns the work (e.g. smart-import),
the domain file POINTS at it and adds only the tasks that plan does not contain. Never two
sources of truth for one task.

## Task ID scheme

`D<domain>.P<phase>.T<n>` — e.g. `D5.P1.T3` = Security domain, phase 1, task 3.
IDs are permanent; never renumber. New tasks append at the end of their phase.

## Task template (every task in every file uses exactly this shape)

```
### D_.P_.T_ — <short imperative name>
**Status:** todo | in-progress | done (YYYY-MM-DD, commit) | blocked (<why>)
**Objective:** one sentence, testable.
**Rationale:** why this exists / what breaks without it.
**Prerequisites:** task IDs + repo facts that must be true first.
**Steps:** numbered, deterministic, no "figure out" verbs.
**Architecture decisions:** choices fixed here so the agent doesn't improvise; DECISION-GATED items flagged.
**Affected files:** real paths (create/modify).
**Acceptance criteria:** observable behaviors, each independently checkable.
**Testing:** exact commands + what must be asserted.
**DoD:** gates green + criteria met + status flipped + erp-status updated.
```

## Execution contract for AI agents (binding, every session)

1. **One task = one session** unless the task file marks a batch. Load: this index + the
   domain file + only the reads the task lists. Do NOT re-explore the repo.
2. **Model ladder:** each task carries a `Model:` hint (Haiku/Sonnet/Opus). Say the hint in
   one line before starting; wait if a downgrade is possible.
3. **Hard rules always on:** tokens-only color, logical CSS, ar/en i18n parity, monochrome
   chrome, money as integer minor units (`apps/web/src/lib/money.ts`), deny-by-default RBAC,
   no new dependency without a written DECISIONS entry first, AI runs as the user (never
   superuser), tool-use never free-text-SQL, writes human-in-the-loop.
4. **Gates before "done":** from `apps/web`: `node scripts/check-i18n-parity.mjs` +
   `npx tsc --noEmit`; repo root: `python scripts/gates/gate03.py`; backend:
   `pytest erp/<app>`. UI work: `conductor-brand` brand-feel checklist too.
5. **Status discipline:** flip the task's `Status:` line in the same commit as the code.
   When every task in a file is done, rename the file with `_done`. Update the `erp-status`
   skill each session.
6. **Blocked ≠ skipped:** record blocker inline in the task + in `erp-status`, stop cleanly.

## Cross-domain dependency spine (coarse)

```
D4 standards ──┐
D5 security ───┼──> D2 architecture (tenancy) ──> D12 SaaS ops ──> D11 marketplace
D6 testing  ───┘            │
D1 core ERP ────────────────┤
D8 data platform ───────────┘
D3 design system ──> (all UI tasks everywhere)
D7 infra/devops ──> D12
D9 integrations: ETA early (D1 needs it), rest after D2 tenancy
D10 customer success: rides smart-import (queue 8) + A2
D13 docs: continuous, hard-gates at each phase exit
```

Rule of thumb: **D4 + D5 + D6 phase-1 tasks are the floor** — they are cheap, unblock
everything, and make weaker agents safe to use. Do them at natural gaps in the main queue.

## Progress convention

The plan folder is the progress bar (same as all Conductor plans): `Status:` lines per task,
`_done` suffix per file. `Docs/OWNER_MANUAL.html` has a founder-facing progress tracker
(checkboxes stored in the browser) — it mirrors, never replaces, the `Status:` lines here.
