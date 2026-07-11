"""Token & cost budgets (ai-reliability T2.7): hard spend ceilings — per request, per user/day,
per org/month — enforced before any provider is called.

Same defensive philosophy as ``gateway/cache.py`` and ``gateway/breaker.py``: a budgets-layer bug
(DB down, missing row) must never break the AI call it fronts. ``check()`` swallows every error
except the one it exists to raise (``BudgetExceeded``) and degrades to "allow"; ``record_spend()``
swallows all of its own errors, same as ``services.tracing``'s own write.

Enforcement is pre-call and estimate-based (no provider has run yet, so the real cost isn't known):
input tokens are estimated from prompt length, output is assumed to use the full ``max_tokens``
ceiling — a deliberate over-estimate, since blocking a call that would have cost less is safe and
under-estimating a budget is not.
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from .. import models as assistant_models
from ..errors import BudgetExceeded

logger = logging.getLogger(__name__)

ORG_KEY = "org"  # single-tenant (customer-hosted): one org-scope row, no real org id needed


def _period_start(scope: str, today: date) -> date:
    """The date-keyed rollup row a call at ``today`` belongs to: the calendar day for ``user``
    (resets at midnight), the first of the month for ``org`` (resets on the 1st)."""
    if scope == assistant_models.Budget.Scope.ORG:
        return today.replace(day=1)
    return today


def _budget(scope: str) -> tuple[int, str] | None:
    """(limit_microcents, action) for a scope, or None if unconfigured — an unconfigured scope
    never blocks (there's nothing to enforce)."""
    try:
        row = assistant_models.Budget.objects.filter(scope=scope).first()
        return (row.limit_microcents, row.action) if row else None
    except Exception:
        logger.exception("budgets: _budget(%s) failed — treating as unconfigured", scope)
        return None


def _spent(scope: str, scope_key: str) -> int:
    try:
        period = _period_start(scope, timezone.now().date())
        row = assistant_models.SpendRollup.objects.filter(
            scope=scope, scope_key=scope_key, period=period).first()
        return row.spend_microcents if row else 0
    except Exception:
        logger.exception("budgets: _spent(%s,%s) failed — treating as 0", scope, scope_key)
        return 0


def estimate_cost_microcents(model: str, input_tokens: int, max_tokens: int) -> int:
    """Worst-case cost of a call before it runs: real input tokens x the full ``max_tokens``
    output ceiling (the call may finish early and cost less — never more)."""
    from ..services.tracing import PRICING

    price = PRICING.get(model)
    if not price:
        return 0  # unpriced model: same "cost_unknown, never guessed" rule as services.tracing
    in_price, out_price = price
    return round(input_tokens * in_price / 1000 + max_tokens * out_price / 1000)


def check(*, estimated_cost: int, actor=None) -> None:
    """Pre-call gate: raise ``BudgetExceeded`` if a ``block``-mode scope is already at or would go
    over its limit with this call. A ``notify``-mode scope over its limit only logs. Any failure
    in this function's own bookkeeping degrades to "allow" — only a real budget breach raises."""
    try:
        _check(estimated_cost=estimated_cost, actor=actor)
    except BudgetExceeded:
        raise
    except Exception:
        logger.exception("budgets: check() failed — allowing the call")


def _over(scope: str, spent: int, estimated_cost: int, limit: int, action: str) -> None:
    if spent + estimated_cost <= limit:
        return
    if action == assistant_models.Budget.Action.BLOCK:
        raise BudgetExceeded(data={"scope": scope})
    logger.warning("budgets: %s scope over limit (notify mode, spend=%d limit=%d)",
                   scope, spent, limit)


def _check(*, estimated_cost: int, actor) -> None:
    req = _budget(assistant_models.Budget.Scope.REQUEST)
    if req is not None:
        _over(assistant_models.Budget.Scope.REQUEST, 0, estimated_cost, *req)

    if actor is not None and getattr(actor, "id", None):
        user_budget = _budget(assistant_models.Budget.Scope.USER)
        if user_budget is not None:
            spent = _spent(assistant_models.Budget.Scope.USER, str(actor.id))
            _over(assistant_models.Budget.Scope.USER, spent, estimated_cost, *user_budget)

    org_budget = _budget(assistant_models.Budget.Scope.ORG)
    if org_budget is not None:
        spent = _spent(assistant_models.Budget.Scope.ORG, ORG_KEY)
        _over(assistant_models.Budget.Scope.ORG, spent, estimated_cost, *org_budget)


def _increment(scope: str, scope_key: str, period: date, cost: int) -> None:
    updated = assistant_models.SpendRollup.objects.filter(
        scope=scope, scope_key=scope_key, period=period,
    ).update(spend_microcents=F("spend_microcents") + cost)
    if updated:
        return
    try:
        assistant_models.SpendRollup.objects.create(
            scope=scope, scope_key=scope_key, period=period, spend_microcents=cost)
    except IntegrityError:
        # Lost the create race to a concurrent call — the row exists now, retry the atomic add.
        assistant_models.SpendRollup.objects.filter(
            scope=scope, scope_key=scope_key, period=period,
        ).update(spend_microcents=F("spend_microcents") + cost)


def record_spend(*, actor=None, cost_microcents: int) -> None:
    """Atomic rollup increment at trace write time — one date-keyed row per scope, no queue.
    Swallows its own errors, same as every other tracing-adjacent write (``services.tracing``)."""
    if not cost_microcents:
        return
    try:
        today = timezone.now().date()
        if actor is not None and getattr(actor, "id", None):
            _increment(assistant_models.Budget.Scope.USER, str(actor.id),
                      _period_start(assistant_models.Budget.Scope.USER, today), cost_microcents)
        _increment(assistant_models.Budget.Scope.ORG, ORG_KEY,
                  _period_start(assistant_models.Budget.Scope.ORG, today), cost_microcents)
    except Exception:
        logger.exception("budgets: record_spend failed — spend not recorded")


def ops_summary() -> list[dict]:
    """Spend vs budget per scope for the ops view. ``request`` has no persisted spend (it's a
    per-call estimate check, nothing to roll up); ``org`` is one directly comparable number
    (single aggregate limit, single aggregate spend); ``user`` shows the current top spender's
    total, the one number directly comparable to a limit that applies equally to every user."""
    try:
        today = timezone.now().date()
        rows = []
        for scope in (assistant_models.Budget.Scope.REQUEST, assistant_models.Budget.Scope.USER,
                     assistant_models.Budget.Scope.ORG):
            b = assistant_models.Budget.objects.filter(scope=scope).first()
            limit_microcents = b.limit_microcents if b else None
            action = b.action if b else None
            if scope == assistant_models.Budget.Scope.REQUEST:
                spend_microcents = None
            elif scope == assistant_models.Budget.Scope.ORG:
                row = assistant_models.SpendRollup.objects.filter(
                    scope=scope, scope_key=ORG_KEY,
                    period=_period_start(scope, today)).first()
                spend_microcents = row.spend_microcents if row else 0
            else:
                row = assistant_models.SpendRollup.objects.filter(
                    scope=scope, period=today).order_by("-spend_microcents").first()
                spend_microcents = row.spend_microcents if row else 0
            rows.append({"scope": scope, "limit_microcents": limit_microcents,
                        "action": action, "spend_microcents": spend_microcents})
        return rows
    except Exception:
        logger.exception("budgets: ops_summary failed")
        return []
