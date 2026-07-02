# Conductor — Core Foundation + Sales Order Workspace — Master Index
# READ THIS FILE FIRST.

## Your job
Build a **greenfield** vertical slice of Conductor: the data foundation, the
trust/posting engine, the permission engine, the tax+currency engine, and ONE
fully working transaction workspace (the **Sales Order**) that demonstrates every
core principle end to end. There is no existing app — you are creating it. Build
**only** the slice described in these files; do not scaffold modules that aren't
listed.

Work **one file at a time, in order**. After each phase, run its verification
block and do not continue until every check passes.

---

## STACK DECISION (change here if the owner disagrees)
The owner is an Oracle / PL-SQL / EBS developer. The trust-critical logic
(posting, tax, FX, mutability) is therefore specified to live **in the database
as the source of truth**, which is also the correct architecture for ERP
integrity. Default stack:

| Layer | Default | Swappable to |
|-------|---------|--------------|
| DB | PostgreSQL 15+ (ANSI SQL; Oracle notes inline) | Oracle 19c+ / APEX |
| Posting/Tax/FX logic | SQL + stored procedures | PL/SQL packages (1:1 mapping noted) |
| API | TypeScript (NestJS), thin — calls DB procedures | Java/Spring, Oracle ORDS |
| Frontend | React + TypeScript | Vue / APEX |

If the owner wants **pure Oracle (APEX + PL/SQL + ORDS)**, the DDL in Phase 1 and
the procedure specs in Phase 2 port directly — keep the same table names, column
names, and procedure contracts; only the syntax changes. Do not invent new names.

> The data model and the engine *rules* (Phases 1–4) are the real product and are
> stack-independent. The UI (Phase 5) is the most stack-specific; treat its code
> as a reference implementation of the contracts, not gospel.

---

## File order
| File | What it does | Risk |
|------|-------------|------|
| 00_START_HERE.md | This file. Golden rules + stack. | None |
| 01_FOUNDATION_AND_SPEC.md | Read principles, scaffold repo, confirm understanding. NO business code. | None |
| 02_PHASE1_DATA_MODEL.md | Core schema: org, currency, fx, tax, party, item, document, state, RBAC, event log. | Low |
| 03_PHASE2_POSTING_TAX_FX.md | The trust core: state machine, mutability matrix, tax+FX engine, GL entries. | Medium |
| 04_PHASE3_PERMISSIONS_API.md | RBAC enforcement (row+field), permission-shaped DTOs, SO API contracts. | Medium |
| 05_PHASE4_WORKSPACE_UI.md | Sales Order workspace: skeleton, single drawer + compare, gated actions, timeline. | Low |
| 06_PHASE5_AI_IN_TRACEABILITY.md | Suggest → human commits → timeline records. Read-only safe AI. | Low |
| 07_VERIFICATION.md | Full invariant suite + how to update this skill. | None |

---

## THE GOLDEN RULES — these outrank everything, in this order
When any two rules conflict, the LOWER NUMBER WINS.

0. **Correctness outranks delight.** Money/tax/inventory/audit are non-negotiable.
1. **Money is typed.** No bare numeric money. Every amount = `(amount, currency, fx_context)`. Tax comes from the engine, never a literal. FX is captured at posting and frozen.
2. **Context respects permission.** Row-level + field-level. Forbidden fields are **absent from the payload**, not hidden in the UI. Actions filtered by permission AND state.
3. **State before edit.** Draft / Posted / Reversed. Posted financials are immutable; change only via Amend or Reverse, which create **linked successors**. Mutability is governed by the matrix in Phase 2 — never by ad-hoc checks.
4. **Total traceability.** Every state change writes an event. AI changes carry `source='ai'` + the human approver.
5. **AI suggests, human commits, timeline records.** No silent financial action by AI, ever.

Print these on the wall. Every phase restates the subset it must honor.

---

## After EVERY file, run the health check
From repo root:
```bash
# DB reachable + migrations applied + invariant smoke test
make verify    # defined in 01; wraps: migrate, lint, unit, invariant-smoke
```
If `make verify` fails, STOP and fix before opening the next file.

## Now open: 01_FOUNDATION_AND_SPEC.md
