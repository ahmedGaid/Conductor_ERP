"""L0 Action Graph — the queryable view of every action's declared semantics.

One place to ask "what does action X need / do": ``get`` returns the declaration,
``unmet_requires`` names the entity kinds a proposal would trip over on an empty (or scoped-away)
database, and ``@register_action`` gives new actions a one-statement registration path that
validates at import time exactly like the built-in registry.

Follow-up path (deep-vision moat #1, deliberately deferred — FILE_00 "Registry home" decision):
a future ``@contract_action`` decorator on module ``contracts.py`` functions would auto-register
here, making every new module agent-operable on day one. Until then, new assistant actions use
``@register_action`` below and module contracts stay untouched.
"""
from __future__ import annotations

from typing import Callable

from erp.accounting import contracts as accounting
from erp.inventory import contracts as inventory
from erp.sales import contracts as sales

from .actions import ACTIONS, Action, _validate_action

# kind -> "does at least one record the actor can see exist?" (reuses the contracts the action
# builders already lean on; customer lookup is actor-scoped, the rest are unscoped master data).
_KIND_EXISTS: dict[str, Callable] = {
    "customer": lambda actor: bool(sales.find_customers(actor, query="", limit=1)),
    "item": lambda actor: bool(inventory.list_items()),
    "warehouse": lambda actor: inventory.default_warehouse_code() is not None,
    "account": lambda actor: bool(accounting.list_accounts()),
}


def get(name: str) -> Action:
    """The declared action, or KeyError — callers decide how to phrase an unknown name."""
    return ACTIONS[name]


def all_actions() -> list[Action]:
    return list(ACTIONS.values())


def unmet_requires(actor, name: str) -> list[str]:
    """Which of the action's required entity kinds have no record the actor can see.

    A kind without a lookup helper is reported as ``"<kind> (unknown)"`` — never raises, so a
    mis-declared requirement degrades to an honest note instead of a crash.
    """
    unmet: list[str] = []
    for kind in get(name).requires:
        exists = _KIND_EXISTS.get(kind)
        if exists is None:
            unmet.append(f"{kind} (unknown)")
        elif not exists(actor):
            unmet.append(kind)
    return unmet


def register_action(*, name: str, description: str, args: dict, **semantics):
    """Register a ``(build_proposal, execute)`` pair as a fully-declared action in one statement.

    Usage::

        @register_action(name="create_x_draft", description="...", args={...},
                         requires=("customer",), effects=(Effect("x", "create"),), risk="draft")
        def _pair():
            return _build_x, _execute_x

    The wrapped callable returns the pair; the decorator builds the ``Action``, validates it with
    the same import-time rules as the built-in registry, and inserts it into ``ACTIONS``. Existing
    actions are NOT migrated — this exists for new actions from Phase A onward.
    """
    def wrap(pair_factory: Callable) -> Action:
        build_proposal, execute = pair_factory()
        action = Action(name, description, args, build_proposal, execute, **semantics)
        _validate_action(action)
        ACTIONS[action.name] = action
        return action
    return wrap
