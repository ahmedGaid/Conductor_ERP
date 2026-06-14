# Workflows

> Saved workflow definitions and the engine contract they run under (Stage 2).

## Engine contract (non-negotiable)
1. Determinism — same definition + inputs + external responses ⇒ same path + same logged result.
2. Node I/O — `run(instance_context, node_config, incoming_payload) -> {status, output_payload, error?}`.
3. State machine — persist after every transition; crash-resumable from the DB.
4. Idempotency on external writes — `sha256(instance_id|node_id|attempt)` + durable ledger + DB UNIQUE.
5. Edge selection — exactly one winner; 0 or ≥2 ⇒ instance fails with a clear message.
6. Approval — set `waiting`, persist, exit; resume on a separate approve/reject event.

## Reference flow (Stage 8)
Purchase Request Approval: start → check_budget → budget_gate → manager_approval → finance_approval
→ create_po (external write) → notify_supplier (webhook) → end. (Re-expressed from the PHASE docs.)
