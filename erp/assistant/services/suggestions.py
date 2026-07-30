"""Blocker → actionable suggestion (plan session 12).

The assistant never stops at "supplier doesn't exist": every dependency blocker becomes a card
answering what's wrong → fastest permitted fix → how we continue after. Permission-filtered HERE,
server-side — the client renders whatever it receives; it never decides what the user may do.

ENTITY_REGISTRY routes are copied verbatim from ``apps/web/src/App.tsx`` — a wrong route here is a
broken promise (``test_suggestions`` guards the list). The create surfaces are the list pages'
inline add forms (there are no ``/new`` routes for these entities), so a create deep link is the
list route carrying a ``?prefill=`` JSON the form consumes (``lib/usePrefill.ts``).
"""
from __future__ import annotations

import json
from urllib.parse import quote

from erp.identity import access
from erp.identity.roles import BRANCH_MANAGER

from . import memory as memory_service
from .actions import ACTIONS, _can

# entity key (blocker vocabulary) → where to fix it + what fixing requires.
#   create_route/list_route/detail_route: real App.tsx paths ({code}/{sku} filled from the blocker)
#   permission_code: the granular code gating a create deep link
#   create_action: the session-10 action that creates it inline from chat, when one exists
#   prefill_field: the create form field the blocker's query lands in
ENTITY_REGISTRY: dict[str, dict] = {
    "customer": {
        "create_route": "/sales/customers",
        "list_route": "/sales/customers",
        "detail_route": "/sales/customers/{key}",
        "permission_code": "sales.customer.create",
        "create_action": "create_customer",
        "prefill_field": "name",
    },
    "supplier": {
        "create_route": "/purchasing/suppliers",
        "list_route": "/purchasing/suppliers",
        "detail_route": "/purchasing/suppliers/{key}",
        "permission_code": "purchasing.supplier.create",
        "create_action": None,
        "prefill_field": "name",
    },
    "item": {
        "create_route": "/inventory/items",
        "list_route": "/inventory/items",
        "detail_route": "/inventory/items/{key}",
        "permission_code": "inventory.item.create",
        "create_action": None,
        "prefill_field": "name",
    },
    "warehouse": {
        "create_route": "/inventory/warehouses",
        "list_route": "/inventory/warehouses",
        "detail_route": "/inventory/warehouses/{key}",
        "permission_code": "inventory.warehouse.create",
        "create_action": None,
        "prefill_field": "name",
    },
}

# The calm alternatives when the actor can't take the fix themselves (blame-free, no dead buttons).
# English on the wire like every tool/action string — the model narrates it in the user's language
# and the card renders its own localized line.
_NO_PERMISSION_CREATE = ("You don't have permission to create this record. Ask an administrator "
                         "to add it, and I'll continue from here once it exists.")
_NO_PERMISSION_FIX = ("You don't have permission to change this setting. Ask an administrator to "
                      "fix it, and I'll continue from here once it's done.")


def _deep_link(reg: dict, query: str, entity: str) -> dict:
    prefill = {reg["prefill_field"]: query} if query else {}
    to = reg["create_route"]
    if prefill:
        to += "?prefill=" + quote(json.dumps(prefill, ensure_ascii=False))
    return {"kind": "deep_link", "label_key": "assistant.suggest.create", "to": to,
            "prefill": prefill, "expect": {"entity": entity, "query": query}}


def build_suggestion(actor, blocker: dict, resume_hint: str = "") -> dict:
    """One blocker → ``{issue, options, no_permission, resume}``.

    Options, in preference order, contain ONLY what the actor can actually use — permission denied
    means no option at all (unavailable ≠ greyed out), with ``no_permission`` carrying the calm
    alternative instead.
    """
    kind = blocker.get("kind") or "missing"
    entity = blocker.get("entity") or ""
    query = str(blocker.get("query") or "").strip()
    issue = {"kind": kind, "entity": entity, "query": query}
    reg = ENTITY_REGISTRY.get(entity)
    options: list[dict] = []
    no_permission: str | None = None

    if kind == "ambiguous":
        # Near-matches exist — picking one IS the fix; no new record, no permission needed beyond
        # the visibility the candidates already came from.
        options.append({"kind": "review_candidates", "entity": entity,
                        "candidates": blocker.get("candidates") or []})
    elif kind == "inactive" and reg is not None:
        edit_code = reg["permission_code"].replace(".create", ".edit")
        if access.has_permission(actor, edit_code):
            options.append({"kind": "open_record", "label_key": "assistant.suggest.open",
                            "to": reg["detail_route"].format(key=query)})
        else:
            no_permission = _NO_PERMISSION_FIX
    elif reg is not None:  # "missing"
        if access.has_permission(actor, reg["permission_code"]):
            # Inline action first (stay in chat) — only when the session-10 action exists AND its
            # own gate passes (actions are role-gated; the granular code alone isn't enough).
            action_name = reg["create_action"]
            if action_name in ACTIONS and _can(actor, BRANCH_MANAGER):
                options.append({"kind": "inline_action", "action": action_name,
                                "args": {"query": query}})
            options.append(_deep_link(reg, query, entity))
        else:
            no_permission = _NO_PERMISSION_CREATE

    return {"issue": issue, "options": options, "no_permission": no_permission,
            "resume": (resume_hint or "").strip()}


def build_memory_proposal(actor, *, now=None) -> dict | None:
    """The pattern-derived memory suggestion (ai-reliability T4.3), or ``None``.

    The detectors are deterministic and read-only (``services/memory.py``); this only shapes the
    card and starts the one-a-day clock, so a user never gets a second nudge the same day even if
    two detectors fire. Confirming or dismissing goes through ``/api/assistant/memory/proposals`` —
    a proposal is never a write.
    """
    proposal = memory_service.next_proposal(actor, now=now)
    if proposal is None:
        return None
    memory_service.mark_proposal_shown(actor, now=now)
    return {
        "kind": "memory_proposal",
        "slot": proposal["slot"],
        "value": proposal["value"],
        "occurrences": proposal["occurrences"],
        "detector": proposal["detector"],
        "options": [{"kind": "confirm_memory", "label_key": "memory.proposal.save"},
                    {"kind": "dismiss_memory", "label_key": "memory.proposal.dismiss"}],
    }
