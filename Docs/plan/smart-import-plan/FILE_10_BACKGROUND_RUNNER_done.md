# SESSION 10 — Background Runner (DECISIONS GATE)
# Files: DECISIONS.md, erp/imports/runner.py (new), erp/imports/management/commands/run_imports.py (new), erp/imports/tests/test_runner.py (new)

---

## ⛔ STOP FIRST — decision required before any code

No worker infrastructure exists in this repo, and roadmap Phase C needs the SAME decision
(scheduled runner). Present the user this choice, write the DECISIONS.md entry, THEN build:

- **Option 1 (recommended baseline): DB-backed job queue + management command.**
  ImportBatch IS the job row. `python manage.py run_imports` loops: claim a `ready` batch
  (select_for_update skip_locked), run `engine.execute_batch`, honor pause/cancel flags
  between chunks. Run under the same process supervisor as the dev/prod server (document
  how in the DECISIONS entry). Zero new dependencies; chunked engine already makes it
  resumable. Phase C's scheduler can reuse the command pattern.
- **Option 2: real worker (Celery/RQ + Redis).** Proper concurrency + retries, but a NEW
  dependency + infra service → needs the full team-rule-7 written decision, ops story for
  customer-hosted installs included.

If the user is unavailable, record the blocker in erp-status and stop the session cleanly —
do NOT default silently (team rule 7).

---

## Before You Start (after the decision)

1. Open `erp/imports/engine.py` → chunk loop, `resume_batch`, progress fields.
2. Find how the repo runs periodic/long tasks today (grep `management/commands` across apps)
   → mirror the command style.

"Do not write anything yet."

---

## Task A — `runner.py` (assuming Option 1; adapt if Option 2 chosen)

```python
def claim_next() -> ImportBatch | None      # select_for_update(skip_locked=True), status ready→running
def run(batch):                              # engine.execute_batch with a per-chunk callback:
    # callback checks batch.control (JSONField added here: {"pause": bool, "cancel": bool}
    # refreshed from DB between chunks) → pause: status=paused, return; cancel: stop,
    # remaining rows → skipped, status=done with cancelled flag.
    # updates stats: rows_done, rows_per_sec (rolling), eta_seconds, stage.
def request_pause/resume/cancel(actor, batch)  # permission-checked control-flag setters
```

Small batches (< IMPORTS_SYNC_LIMIT, default 500 rows) run inline in the API request —
no runner round-trip for the common small file (spec: "extremely fast").

## Task B — Management command + crash recovery

`run_imports` command: loop with idle sleep; `--once` flag for tests/cron. On startup, any
batch stuck `running` with a stale heartbeat (stats["heartbeat"] older than 5 min) →
`resume_batch` (spec step 20 recovery). Heartbeat written per chunk.

## Task C — Tests

Claim is exclusive under two concurrent claimers. Pause between chunks → paused with partial
durable progress → resume completes. Cancel skips the remainder. Stale-heartbeat batch gets
recovered by a fresh runner. Inline path used under the sync limit.

---

## Smoke Test

- [ ] DECISIONS.md entry written and the choice implemented matches it
- [ ] 5k-row batch: `run_imports --once` processes it; progress/speed/ETA fields fill live
- [ ] Pause → resume → done, counts exact; cancel leaves durable imported rows + skipped rest
- [ ] Kill -9 mid-batch → next runner run resumes automatically
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?  ← MERGE CHECKPOINT: backend engine complete — gates green, merge to main.
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_11_IMPORT_API.md in a FRESH session.
```
