# SESSION 9 — Execution Engine: Strategies, Chunked Commits, Rollback
# Files: erp/imports/engine.py (new), erp/imports/tests/test_engine.py (new)

---

## Before You Start

1. Open `erp/imports/models.py` → ImportBatch.strategy choices, ImportRow.status/result_ref.
2. Open `erp/audit/services.py` → `record(...)` — engine writes ONE audit entry per chunk
   (module="imports", counts in after), adapters' service calls already audit per record.
3. Open `erp/imports/adapters/crm.py` → `write`/`exists`; find whether module services expose
   an UPDATE function per entity — update/upsert strategies need it; where absent, that
   entity supports create-only + skip (declare `supports_update = False` on the adapter).

"Do not write anything yet."

---

## Task A — `engine.py::execute_batch`

```python
CHUNK = 200  # rows per transaction — small enough to keep locks short, big enough to be fast

def execute_batch(actor, batch) -> None:
    """Readiness gate first: no undecided duplicates? no error rows unless user chose
    'continue after errors'? creation plan resolved? strategy set? else raise Ready-Error
    listing what's missing (actionable).
    Then per chunk of pending rows, inside ONE transaction.atomic():
      per row → strategy dispatch:
        create_only: exists? → skip : write
        update_only: exists? → update : skip
        upsert:      exists? → update : write
        skip_existing: exists? → skip : write
      row.result_ref = {model, pk, action}; row.status = imported/skipped
      chunk fails mid-way → that transaction rolls back, rows stay pending,
      batch.status stays running, error recorded → NEXT chunk continues or engine stops
      per the 'continue after errors' flag.
    batch.processed_count updated per chunk (progress signal). All statuses persisted —
    a killed process resumes with resume_batch(): pending rows only, already-imported
    chunks are durable (spec step 20 'recovery after interruption')."""
```

Full-rollback mode (small batches ≤ CHUNK×5): optional single wrapping transaction when the
user picked "all or nothing" — expose as `batch.stats["atomicity"]: "chunked"|"all"`.

## Task B — `engine.py::rollback_batch` (index decision 7)

```python
def rollback_batch(actor, batch) -> dict:
    """Reverse order of import. Per row with result_ref:
    - created master, unreferenced by later data → delete via module service delete-path
      (if none exists → mark 'cannot_revert' with reason)
    - created document (draft) → module service delete/cancel
    - posted/referenced records → cannot_revert (reversal by contra is a HUMAN accounting
      decision — the report links the records instead)
    - updated records → cannot_revert baseline (no before-image v1; note in DECISIONS)
    Also reverts batch.stats['created_masters']. Returns {reverted, skipped, cannot: [...]}.
    batch.status = rolled_back. Audit entry."""
```

## Task C — Report data (spec step 22 backend)

`engine.build_report(batch) -> dict`: imported/updated/skipped/errors/warnings/created-masters/
duration/by-entity counts + per-row outcome list (streamed CSV export in session 11's API).

## Task D — Tests

Each strategy against pre-seeded records. Chunk-2 crash (mock write raising on row N) → chunk N
rolled back, chunks <N durable, resume completes the rest, no row imported twice (idempotence:
pending-only selection). Readiness gate blocks undecided duplicates. Rollback deletes created
masters, marks posted docs cannot_revert. Audit entries per chunk.

---

## Smoke Test

- [ ] 1k rows import in chunks; kill/resume test passes; zero double-imports
- [ ] All four strategies behave per table above; upsert on adapter with supports_update=False → readiness error
- [ ] Rollback of a masters-only batch leaves DB as before (minus audit trail)
- [ ] Report dict counts reconcile exactly with row statuses
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_10_BACKGROUND_RUNNER.md in a FRESH session.
```
