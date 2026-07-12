"""L2 simulation engine — dry-run a plan of write-actions inside one rolled-back transaction and
collect a structured diff (os-foundations FILE_04).

Fidelity is hybrid (founder-approved, ``Docs/plan/os-foundations-plan/FILE_00_INDEX.md``): each
step runs through the REAL ``actions.build()`` / ``actions.execute()`` / verifier path, inside one
``transaction.atomic()`` that always rolls back — nothing persists. ``sim_mode()`` is a
``contextvars.ContextVar`` flag (thread/async-safe, no settings sprawl) that the few external
side-effect choke points (notification dispatch, e-invoice submission, workflow adapter calls)
check to no-op instead of acting for real. None of the 17 registered actions reach those paths
today (verified by grep — see FILE_04 T4.1), so the stubs are inert future-proofing for when a
post-risk action (Phase B) starts reaching them, not exercised by any live action yet.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from erp.accounting.services.reports import trial_balance
from erp.audit import services as audit
from erp.core.errors import AppError
from erp.inventory.services.reports import stock_on_hand
from erp.purchasing.domain.models import PurchaseOrder
from erp.sales.domain.models import SalesOrder

from . import actions
from ..errors import ActionFailedError, ActionForbiddenError
from ..verifier import run as verify_run

# --- sim-mode flag + collector (T4.1) --------------------------------------------------------

_active: contextvars.ContextVar[bool] = contextvars.ContextVar("sim_mode_active", default=False)
_skips: contextvars.ContextVar[list[dict] | None] = contextvars.ContextVar(
    "sim_mode_skips", default=None
)


def in_sim_mode() -> bool:
    """True while inside a ``sim_mode()`` block — external side-effect choke points check this."""
    return _active.get()


def record_skip(kind: str) -> None:
    """Called by a stubbed choke point instead of doing the real external write."""
    skips = _skips.get()
    if skips is not None:
        skips.append({"skipped": kind})


def sim_skips() -> list[dict]:
    """Skip records collected so far in the current ``sim_mode()`` block (``[]`` outside one)."""
    return list(_skips.get() or [])


@contextmanager
def sim_mode():
    """Mark the current context as a dry run for the choke points above."""
    active_token = _active.set(True)
    skips_token = _skips.set([])
    try:
        yield
    finally:
        _active.reset(active_token)
        _skips.reset(skips_token)


# --- simulate() (T4.2 + T4.3) ------------------------------------------------------------------

@dataclass(frozen=True)
class PlanStep:
    action: str   # registered action name
    args: dict    # what actions.build() takes as the decision


class _Rollback(Exception):
    """Always raised at the end of the simulated transaction — never anything else."""


# Entities whose model carries an ``outstanding_minor`` the diff can read straight off a freshly
# created row (money rule: minor units on the wire). Extend here if a future archetype needs it.
_RECEIVABLE_MODELS = {"sales_order": SalesOrder}
_PAYABLE_MODELS = {"purchase_order": PurchaseOrder}


def _step_error_summary(proposal: dict) -> str:
    if "error" in proposal:
        return proposal["error"]
    blocker = proposal["blocker"]
    return f"Missing {blocker['entity']} '{blocker['query']}'."


def _stock_pairs(payload: dict) -> list[tuple[str, str]]:
    """(item_sku, warehouse_code) pairs a step's payload touches, for a step whose action declares
    ``stock="moves"``. No current action does (see module docstring) — this only fires once a
    future action opts in, using the field names the codebase already uses for warehouse codes."""
    sku = payload.get("item_sku")
    if not sku:
        return []
    codes = [payload[k] for k in ("warehouse_code", "source_code", "destination_code")
             if payload.get(k)]
    return [(sku, code) for code in codes]


def _on_hand(item_sku: str, warehouse_code: str) -> str:
    balance = stock_on_hand(item_sku=item_sku, warehouse_code=warehouse_code)
    return balance.rows[0].quantity if balance.rows else "0"


def simulate(actor, steps: list[PlanStep]) -> dict:
    """Run ``steps`` for real inside a transaction that always rolls back; return the diff."""
    result_steps: list[dict] = []
    creates: dict[str, int] = {}
    stock_before: dict[tuple[str, str], str] = {}
    stock_after: dict[tuple[str, str], str] = {}
    receivables_after = 0
    payables_after = 0
    ok = True
    tb_before = tb_after = None

    with sim_mode():
        try:
            with transaction.atomic():
                tb_before = trial_balance()
                for step in steps:
                    proposal = actions.build(actor, step.action, step.args)
                    if "error" in proposal or "blocker" in proposal:
                        result_steps.append({"action": step.action,
                                             "summary": _step_error_summary(proposal),
                                             "ok": False})
                        ok = False
                        break

                    action_def = actions.ACTIONS.get(step.action)
                    payload = proposal["payload"]
                    touches_stock = action_def is not None and any(
                        e.stock == "moves" for e in action_def.effects
                    )
                    if touches_stock:
                        for sku, wh in _stock_pairs(payload):
                            stock_before.setdefault((sku, wh), _on_hand(sku, wh))

                    try:
                        result = actions.execute(actor, step.action, payload)
                    except PermissionError:
                        result_steps.append({"action": step.action,
                                             "summary": ActionForbiddenError.message,
                                             "ok": False})
                        ok = False
                        break
                    except AppError as exc:
                        result_steps.append({"action": step.action, "summary": exc.message,
                                             "ok": False})
                        ok = False
                        break
                    except Exception:
                        result_steps.append({"action": step.action,
                                             "summary": ActionFailedError.message, "ok": False})
                        ok = False
                        break

                    scope = {"links": result.get("links") or [], "payload": payload,
                             "actor": actor}
                    invariants = action_def.invariants if action_def else ()
                    report = verify_run(invariants, scope) if invariants else None
                    step_ok = report.ok if report is not None else True
                    result_steps.append({
                        "action": step.action, "summary": result.get("summary"), "ok": step_ok,
                        "verifier": ({"ok": report.ok,
                                     "packs": [f.pack for f in report.findings]}
                                    if report is not None else {"ok": True, "packs": []}),
                    })
                    if not step_ok:
                        ok = False
                        break

                    link_value = (result.get("links") or [{}])[0].get("value")
                    for effect in (action_def.effects if action_def else ()):
                        if effect.verb == "create":
                            creates[effect.entity] = creates.get(effect.entity, 0) + 1
                        if effect.entity in _RECEIVABLE_MODELS and link_value:
                            row = _RECEIVABLE_MODELS[effect.entity].objects.get(id=link_value)
                            receivables_after += row.outstanding_minor
                        if effect.entity in _PAYABLE_MODELS and link_value:
                            row = _PAYABLE_MODELS[effect.entity].objects.get(id=link_value)
                            payables_after += row.outstanding_minor

                for sku, wh in stock_before:
                    stock_after[(sku, wh)] = _on_hand(sku, wh)
                tb_after = trial_balance()
                raise _Rollback()
        except _Rollback:
            pass

    stock_diff = [
        {"item": sku, "warehouse": wh,
         "delta": str(Decimal(stock_after[(sku, wh)]) - Decimal(stock_before[(sku, wh)]))}
        for sku, wh in stock_before
    ]
    diff = {
        "ok": ok,
        "steps": result_steps,
        "creates": creates,
        "gl": {
            "debit_delta_minor": (tb_after.total_debit - tb_before.total_debit
                                  if tb_before is not None and tb_after is not None else 0),
            "credit_delta_minor": (tb_after.total_credit - tb_before.total_credit
                                   if tb_before is not None and tb_after is not None else 0),
        },
        "stock": stock_diff,
        "money": {
            "receivables_delta_minor": receivables_after,
            "payables_delta_minor": payables_after,
        },
    }
    audit.record(module="assistant", action="simulate", entity_type="Plan", actor=actor,
                 after={"ok": ok, "steps": len(result_steps), "creates": creates})
    return diff
