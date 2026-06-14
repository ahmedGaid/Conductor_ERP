"""workflow — graph-based workflow orchestration engine.

Deterministic, crash-resumable state machine that drives a workflow instance node-by-node,
persisting after every transition, honoring idempotency, retry, and edge-selection rules.
See architecture/workflows.md for the non-negotiable engine contract.
"""
