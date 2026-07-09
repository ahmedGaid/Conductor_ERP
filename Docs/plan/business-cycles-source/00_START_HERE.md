# Conductor — Business Cycles Expansion — Master Index
# READ THIS FILE FIRST. Do not open any other file until you finish this one.

## Your job

The Sales Order vertical slice (instruction files 00–07 of the original plan) is ALREADY WORKING.
You are now expanding Conductor from a single document workspace into complete **business cycles**.
You are ADDING only. Nothing in the existing slice is deleted, renamed, or restructured.

The expansion strategy (decided by the product owner, not negotiable):

1. **Think in cycles, not modules.** You will never build "the Inventory module" or "the AR module"
   as standalone units. You build document chains that complete a business cycle end-to-end.
2. **Cycle order is fixed:**
   - Phase 1–2: complete **Order-to-Cash** (Sales Order → Delivery → AR Invoice → Receipt → GL event)
   - Phase 3: **ETA e-invoice lifecycle** as NATIVE document states inside O2C (not an export feature)
   - Phase 4: **Procure-to-Pay** (Purchase Order → Goods Receipt → Supplier Invoice → 3-way match → Payment)
   - Phase 5: **Record-to-Report** foundation (journal events, accounting periods, period close guard)
3. **Depth from Oracle EBS, surface from Odoo.** The data model answers the same questions EBS answers
   (what creates what, which quantities are tracked, when accounting is frozen). The visible surface
   stays SME-simple: every screen exposes the minimum field set; everything else is progressive disclosure.
   Simplification lives in the number of VISIBLE options, never in the correctness of the model underneath.

## Architecture constraints inherited from the existing slice — these must never be broken

| # | Golden rule (existing) | Applies here as |
|---|------------------------|-----------------|
| G-CORRECTNESS | Correctness principles (rank 0–4) outrank UX principles (rank 5–12) | Every phase: model first, screen second |
| G-MONEY | Typed money columns; FX rate frozen at posting time | Every new document with amounts |
| G-MUTABILITY | Editable fields are data in `field_mutability`, never conditional code | Every new document type and state |
| G-RBAC | Row-level + field-level RBAC; forbidden fields are ABSENT from payloads | Every new endpoint |
| G-EVENTS | Every mutation logged via database triggers to the universal event log | Every new table |
| G-WRITE-PATH | All writes (human or AI) go through the guarded stored-procedure write path | Every new document action |

## New golden rules introduced by this instruction set

| # | Rule |
|---|------|
| C1 | Every document line that flows to another document tracks quantities as separate columns: `qty_ordered`, `qty_delivered`, `qty_invoiced`, `qty_cancelled`. Derived "open" quantity is computed, never stored. |
| C2 | `qty_delivered + qty_cancelled <= qty_ordered` and `qty_invoiced <= qty_delivered` (service lines: `qty_invoiced <= qty_ordered`). Enforced by constraint/trigger, not by UI. |
| C3 | Document chaining is data: every document row records `source_doc_type` + `source_doc_id` + line-level `source_line_id`. No document is created from another except through a chain procedure. |
| C4 | ETA e-invoice status is part of the invoice state machine (`eta_pending → eta_submitted → eta_accepted / eta_rejected`), stored on the document, transitioned only through the guarded write path. A posted invoice that is ETA-rejected is NOT editable — it is credited and re-issued. |
| C5 | 3-way match: a supplier invoice cannot move to `matched` unless invoice qty ≤ received qty per line and price variance is within tolerance. Tolerances are data in a table, not constants in code. |
| C6 | No document may post into a closed accounting period. The period guard runs inside the posting procedure, not in the API layer. |
| C7 | Every posting produces journal event rows (debit/credit pairs that balance per currency) in the same transaction as the document state change. |
| C8 | Cancellations and corrections are forward-only: reversal/credit documents, never destructive edits of posted rows. |

## File order

| File | What it does | Risk |
|------|--------------|------|
| 00_START_HERE.md | This file | None |
| 01_READ_CODEBASE.md | Read existing slice, confirm understanding | None |
| 02_PHASE1_O2C_SPINE.md | Delivery + AR Invoice documents, quantity tracking, document chain | Low (additive schema) |
| 03_PHASE2_O2C_CASH.md | Customer Receipt + application to invoices | Low |
| 04_PHASE3_ETA_LIFECYCLE.md | ETA states in the invoice state machine | Low |
| 05_PHASE4_P2P.md | PO, Goods Receipt, Supplier Invoice, 3-way match, Payment | Medium (largest phase) |
| 06_PHASE5_R2R.md | Journal events, accounting periods, period close guard | Medium (touches posting path) |
| 07_VERIFICATION.md | Full invariant suite + Makefile targets + skill update | None |

## After every single file, run:

```bash
make verify        # existing invariant suite must stay green
make verify-cycles # new suite added incrementally by these phases
```

If `make verify` breaks at any point, STOP. Fix before continuing. The existing slice is production truth.

## Now open: 01_READ_CODEBASE.md
