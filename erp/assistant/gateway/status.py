"""Assistant health surface (ai-reliability T2.9): the truth about AI health, calmly.

``mode`` derives from breaker state (T2.3) and budget spend (T2.7) — no separate health
tracking, just a read of state the gateway already keeps.

- ``full`` — every configured provider is breaker-closed and no ``block``-mode budget is
  exhausted.
- ``degraded`` — at least one provider is skipped (breaker open or half-open) or a
  ``block``-mode budget is exhausted, but a usable provider remains: calls still answer,
  just on a fallback chain or blocked for some callers.
- ``down`` — every provider is breaker-open: the next call would raise ``AllProvidersDown``
  without even trying a runner.
"""
from __future__ import annotations

from .. import client
from . import breaker, budgets


def mode() -> str:
    chain = client.provider_chain()
    states = {p: breaker.state(p) for p in chain}
    usable = [p for p in chain if states[p] != "open"]
    if not usable:
        return "down"
    degraded_provider = any(s != "closed" for s in states.values())
    degraded_budget = any(
        row["action"] == "block"
        and row["limit_microcents"] is not None
        and row["spend_microcents"] is not None
        and row["spend_microcents"] >= row["limit_microcents"]
        for row in budgets.ops_summary()
    )
    return "degraded" if (degraded_provider or degraded_budget) else "full"
