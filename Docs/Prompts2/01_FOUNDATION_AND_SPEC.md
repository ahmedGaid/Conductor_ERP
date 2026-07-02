# Phase 0 — Foundation & Spec Confirmation
# NO BUSINESS CODE IN THIS FILE. Scaffold + read + confirm only.

## Read first (in this order)
1. `00_START_HERE.md` — the golden rules. You will be quizzed below.
2. The 13 principles the owner approved (also embedded as golden rules in 00).
3. Nothing else exists yet — this is greenfield.

## Scaffold the repo (additive only — empty project)
Create this structure. Do **not** add modules beyond what's listed.
```
conductor/
  db/
    migrations/        # numbered SQL files, applied in order
    seed/              # reference data: currencies, tax codes, roles
  api/                 # thin transport layer over DB procedures
    src/
  web/                 # React workspace
    src/
  tests/
    invariants/        # the correctness suite (the heart of CI)
  Makefile
```

### Makefile (create exactly this; commands referenced by every phase)
```make
DB_URL ?= postgres://conductor:conductor@localhost:5432/conductor

migrate:        ## apply all db/migrations in order
	@for f in $$(ls db/migrations/*.sql | sort); do echo "applying $$f"; psql "$(DB_URL)" -v ON_ERROR_STOP=1 -f $$f; done

seed:
	@for f in $$(ls db/seed/*.sql | sort); do psql "$(DB_URL)" -v ON_ERROR_STOP=1 -f $$f; done

invariant-smoke:
	psql "$(DB_URL)" -v ON_ERROR_STOP=1 -f tests/invariants/smoke.sql

verify: migrate seed invariant-smoke
	@echo "VERIFY OK"
```
For Oracle: replace `psql` with `sqlplus`/`sql` and `DB_URL` with a connect
string; keep target names identical.

## Confirmation questions — answer before writing ANY schema
1. When a UX principle conflicts with a correctness principle, which wins, and why?
2. A salesperson opens a posted invoice. The `margin` field is sensitive. Where is `margin` allowed to exist in the response payload sent to that user? (Answer must be: nowhere.)
3. Can a posted invoice's `total_amount` be edited directly? If not, what are the only two ways its financial effect can change?
4. When is the FX rate for a document captured, and may it ever be recomputed afterward?
5. Who/what is allowed to make a financial change with no human in the loop?
6. What does every single state change (in any table) have to produce, without exception?
7. Name the three document states and one field that is mutable in `Posted` state.

## Forbidden patterns — memorize
- ❌ A money column without a paired currency column.
- ❌ A tax amount computed inline (`amount * 0.14`) anywhere.
- ❌ Recomputing FX after posting.
- ❌ A query that returns sensitive fields and trusts the UI to hide them.
- ❌ An `UPDATE` on a posted document's financial columns.
- ❌ Any mutation that does not also insert an `event_log` row.
- ❌ Stacking multiple drawers (UI). One dynamic drawer; compare = split view.

## After answering correctly
Run `make migrate` (it should succeed on an empty migrations dir / no-op), then
open `02_PHASE1_DATA_MODEL.md`.

## Next file: 02_PHASE1_DATA_MODEL.md
