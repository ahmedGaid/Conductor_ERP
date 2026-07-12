# FILE_04 — L2: Simulation engine (dry-run a plan, collect the diff)

> ONE SESSION. Prereq: FILE_01–03 `_done`. Backend-only; the API + diff card UI are FILE_05.

## Why

`simulate(plan)` = run the real writes inside one transaction that always rolls back, and hand
back what WOULD have happened. Import preview (Phase A) and month-close preview (Phase B) become
consumers of this instead of bespoke code. Founder-approved fidelity: **hybrid** — real
`execute()`, rolled back, external side effects stubbed.

## Design

NEW `erp/assistant/services/simulation.py`:

```python
@dataclass(frozen=True)
class PlanStep:
    action: str      # registered action name
    args: dict       # what actions.build() takes as the decision

def simulate(actor, steps: list[PlanStep]) -> dict   # the diff, shape below
```

Execution:

```
with sim_mode():                       # ContextVar flag (decision point below)
    try:
        with transaction.atomic():
            for i, step in enumerate(steps):
                proposal = actions.build(actor, step.action, step.args)
                if "error" in proposal or "blocker" in proposal: record step failure; break
                result = actions.execute(actor, step.action, proposal["payload"])
                report = verifier.run(invariants, scope)          # same as FILE_03
                collect(i, proposal, result, report)
            snapshot deltas (see Diff collection)
            raise _Rollback                                        # ALWAYS — nothing persists
    except _Rollback:
        pass
audit.record(module="assistant", action="simulate", ...)           # OUTSIDE the atomic — persists
```

**Sim-mode stubs** — inside `sim_mode()`, these do nothing and record that they were skipped:
- notifications dispatch (`erp/notifications` send path)
- e-invoice submission (`erp/einvoice` ETA client call path)
- any workflow external-write adapter call (`erp/workflow/adapters`)

Mechanism: each stub point checks the ContextVar at its own choke point (one `if` per site, ~3
sites). Grep each path first; if a site can't be reached by any current action's `execute`,
document it as not-reachable instead of stubbing blind.
Doc numbers need NO stub: `_next_number()` is SELECT-max+1 everywhere (verified 2026-07-12:
sales/quotations/purchasing/accounting/crm) — rollback restores them.

**Diff collection** (deterministic, from L0 `effects` — not from model text):
- per step: action name, summary, ok/failed, verifier report
- records: counts per `Effect.entity` + the would-be links (from each `result["links"]`)
- GL impact: `trial_balance` totals before vs after (delta per side)
- stock impact: touched item/warehouse balance before vs after (from steps whose effects declare
  stock)
- receivables/payables deltas where a touched document carries them (sales order outstanding,
  purchase order outstanding)

Diff shape (the FILE_05 card renders exactly this):

```json
{
  "ok": true,
  "steps": [{"action": "...", "summary": "...", "ok": true, "verifier": {...}}],
  "creates": {"customer": 3, "sales_order": 14},
  "gl": {"debit_delta_minor": 0, "credit_delta_minor": 0},
  "stock": [{"item": "SKU-1", "warehouse": "WH-1", "delta": "-3"}],
  "money": {"receivables_delta_minor": 4230000}
}
```

A mid-plan failure (blocker/error/verifier fail) stops the plan, keeps earlier steps' diff
contribution, sets `ok: false`, and names the failing step — this is exactly what
proposal-level aggregation could never catch, and why hybrid won.

## Tasks

### [ ] T4.1 — `sim_mode` ContextVar + the stub sites

- **Goal:** inside `sim_mode()`, the three external side-effect paths no-op and report skipped.
- **Decision point (ask user before starting):** ContextVar in `simulation.py` (recommended) vs
  request attribute. If approved, proceed; if denied, implement the chosen alternative.
- **Files:** NEW `erp/assistant/services/simulation.py` (flag + context manager); the 2–3 stub
  sites found by grepping notification-send / ETA-submit / adapter-call paths; NEW
  `erp/assistant/tests/test_simulation.py`.
- **Steps:** implement `sim_mode()`; add the choke-point checks; each records
  `{"skipped": "<kind>"}` into a sim-scoped collector.
- **Accept:** test: inside `sim_mode()`, the notification path writes nothing and the collector
  shows the skip; outside, behaviour unchanged (regression test).
- **Output:** dry-runs cannot leak side effects.

### [ ] T4.2 — `simulate()` core: rolled-back execution + step results

- **Goal:** a 2-step plan (create customer → create sales order for them) simulates end-to-end;
  DB row counts identical before/after.
- **Files:** `simulation.py`; `test_simulation.py`.
- **Steps:** implement the execution block above. Step N sees step N-1's writes (same
  transaction) — assert this in the test (the order resolves the just-created customer).
  Mid-plan failure test: step 2 references a nonexistent item → `ok: false`, failing step named,
  nothing persisted.
- **Accept:** `pytest erp/assistant/tests/test_simulation.py` green; row counts prove rollback;
  the audit `simulate` record persists (written outside the atomic).
- **Output:** the L2 engine — "see tomorrow's books" is now computable.

### [ ] T4.3 — Diff collection

- **Goal:** the JSON shape above, filled from L0 effects + before/after snapshots.
- **Files:** `simulation.py`; `test_simulation.py`.
- **Steps:** snapshot `trial_balance` totals + touched stock balances before the loop and before
  the rollback; build `creates` from executed steps' declared effects; pull money deltas from
  touched documents. All integers in minor units on the wire (money rule).
- **Accept:** test: the 2-step plan's diff shows `creates == {"customer": 1, "sales_order": 1}`
  and the expected receivables delta; a plan touching no stock yields `stock: []`.
- **Output:** a renderable diff — FILE_05 consumes it verbatim.

## After this session

`pytest erp/assistant` green → commit (`feat(assistant): os-foundations L2 — simulation engine`)
→ check boxes → rename `_done` → update `erp-status` → fresh session for FILE_05.
