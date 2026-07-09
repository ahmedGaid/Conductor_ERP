# Phase 0 — Read Codebase & Confirm Understanding
# NO CODE IN THIS FILE. Reading and answering only.

## Files to read (in order)

1. The original instruction set `00`–`07` (Sales Order vertical slice) — skim all, read `schema` and `write path` files fully.
2. `db/migrations/` — every migration touching: sales order tables, `field_mutability`, event log triggers, RBAC tables.
3. The stored procedure implementing the guarded write path (the single entry point for document mutations).
4. The stored procedure or trigger that freezes FX at posting time.
5. `field_mutability` seed data — how states map to editable field sets for Sales Order.
6. The event log trigger template — how new tables get wired into universal logging.
7. RBAC field-shaping code in the NestJS layer — how forbidden fields are stripped from payloads.
8. The Sales Order workspace React components — layout skeleton, command palette wiring, timeline component.
9. `Makefile` — every `verify-*` target and which golden rule number each maps to.
10. Any Oracle porting notes files (`*oracle*.md`) — you will extend them, matching their style.

## Confirmation questions — answer ALL in your first response before writing any code

1. What is the exact name and signature of the guarded write-path procedure, and what does it return on a mutability violation?
2. In which table and columns is the frozen FX rate stored for a posted Sales Order, and at what state transition is it captured?
3. How does a new table get enrolled in the universal event log — trigger per table, or a generic trigger function? Name the function.
4. What are the existing Sales Order states, and where is the state machine defined (table, enum, or procedure)?
5. How does `field_mutability` encode "field X editable in state Y for doc type Z"? Give the actual column names.
6. In the NestJS layer, at what point are RBAC-forbidden fields removed — serializer, interceptor, or SQL projection?
7. Which Makefile target checks event-log completeness, and what golden rule number is it mapped to?
8. Does the Sales Order line table already have any quantity columns beyond `qty_ordered`? List what exists.

## Forbidden patterns — memorize these

- NEVER write to a document table with direct `INSERT`/`UPDATE` from NestJS. Only the guarded write path.
- NEVER encode "which fields are editable" as `if (status === ...)` in TypeScript or React. It is data in `field_mutability`.
- NEVER store computed quantities (e.g. `qty_open`). Compute in views/queries.
- NEVER delete or edit a posted row to "fix" it. Reversal documents only (rule C8).
- NEVER put ETA logic in a scheduled export job detached from document state (rule C4).
- NEVER hardcode match tolerances, tax rates, or period dates in procedures (rules C5, C6).
- NEVER add a UI field without adding its `field_mutability` rows and RBAC field entries in the same phase.

## After answering correctly

Run `make verify` — must be green before you touch anything.

## Next file: 02_PHASE1_O2C_SPINE.md
