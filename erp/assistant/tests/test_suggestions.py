"""Guided detours (plan session 12) — blocker → permission-filtered actionable suggestion.

Two seams are pinned: ``actions.build`` upgrading dependency-shaped failures into the blocker
vocabulary (missing / inactive / ambiguous, with candidates), and ``build_suggestion`` turning a
blocker into only the options the actor can actually use. The registry's routes are guarded against
a hardcoded copy of the App.tsx route list — a wrong route is a broken promise, so the guard fails
loudly if App.tsx moves a route without updating the registry.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import override_settings

from erp.assistant.services import actions, suggestions
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.inventory.domain.models import Item, Warehouse
from erp.purchasing.domain.models import Supplier
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _admin(username: str = "sug_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _nobody(username: str = "sug_nobody") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _with_code(username: str, group: str, code: str) -> User:
    """Holds the granular permission code, but NOT the Branch Manager role."""
    u = _nobody(username)
    g, _ = Group.objects.get_or_create(name=group)
    RolePermission.objects.update_or_create(role=g, code=code, defaults={"scope": "all"})
    u.groups.add(g)
    return u


# --- actions.build emits the blocker vocabulary ---------------------------------------------------

def test_missing_customer_becomes_blocker_not_error():
    result = actions.build(_admin(), "create_sales_order_draft",
                           {"customer": "Zzz Nonexistent", "items": [{"item": "X", "quantity": "1"}]})
    assert "error" not in result
    block = result["blocker"]
    assert block["kind"] == "missing"
    assert block["entity"] == "customer"
    assert block["query"] == "Zzz Nonexistent"


def test_ambiguous_supplier_blocker_carries_candidates():
    Supplier.objects.create(code="S-1", name="Cairo Supplies")
    Supplier.objects.create(code="S-2", name="Cairo Supply Co")
    # "Cairo" scores in the near-match band (≥0.4, below the 0.6 accept bar) for both names.
    result = actions.build(_admin(), "create_purchase_request_draft",
                           {"supplier": "Cairo", "items": [{"item": "X", "quantity": "1"}]})
    block = result["blocker"]
    assert block["kind"] == "ambiguous"
    assert block["entity"] == "supplier"
    assert {c["code"] for c in block["candidates"]} == {"S-1", "S-2"}


def test_inactive_warehouse_becomes_inactive_blocker():
    Customer.objects.create(code="C-1", name="Nile Traders")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-OFF", name="Closed", is_active=False)
    result = actions.build(_admin(), "create_sales_order_draft",
                           {"customer": "Nile Traders", "warehouse": "WH-OFF",
                            "items": [{"item": "SKU-1", "quantity": "1"}]})
    block = result["blocker"]
    assert block == {"kind": "inactive", "entity": "warehouse", "query": "WH-OFF"}


# --- build_suggestion: permission-aware options ----------------------------------------------------

def _missing_customer():
    return {"kind": "missing", "entity": "customer", "query": "ABC Trading"}


def test_permitted_actor_gets_inline_action_and_deep_link():
    s = suggestions.build_suggestion(_admin(), _missing_customer(), "I'll prepare the order.")
    kinds = [o["kind"] for o in s["options"]]
    assert kinds == ["inline_action", "deep_link"]  # inline (stay in chat) preferred first
    inline = s["options"][0]
    assert inline["action"] == "create_customer" and inline["args"] == {"query": "ABC Trading"}
    link = s["options"][1]
    assert link["to"].startswith("/sales/customers?prefill=")
    assert link["prefill"] == {"name": "ABC Trading"}
    assert link["expect"] == {"entity": "customer", "query": "ABC Trading"}
    assert s["no_permission"] is None
    assert s["resume"] == "I'll prepare the order."


def test_code_without_role_gets_deep_link_only():
    # Holds sales.customer.create but not the Branch Manager role the inline action requires.
    u = _with_code("sug_codeonly", "SalesOps", "sales.customer.create")
    s = suggestions.build_suggestion(u, _missing_customer(), "")
    assert [o["kind"] for o in s["options"]] == ["deep_link"]
    assert s["no_permission"] is None


def test_unpermitted_actor_gets_no_options_and_calm_text():
    s = suggestions.build_suggestion(_nobody(), _missing_customer(), "")
    assert s["options"] == []  # unavailable ≠ greyed out: no dead buttons
    assert s["no_permission"]


def test_ambiguous_blocker_returns_candidate_review():
    block = {"kind": "ambiguous", "entity": "supplier", "query": "Cairo",
             "candidates": [{"code": "S-1", "name": "Cairo Supplies", "score": 0.55}]}
    s = suggestions.build_suggestion(_nobody(), block, "")
    assert [o["kind"] for o in s["options"]] == ["review_candidates"]
    assert s["options"][0]["candidates"][0]["code"] == "S-1"


def test_inactive_blocker_links_to_the_record_settings():
    block = {"kind": "inactive", "entity": "warehouse", "query": "WH-OFF"}
    s = suggestions.build_suggestion(_admin(), block, "")
    assert s["options"] == [{"kind": "open_record", "label_key": "assistant.suggest.open",
                             "to": "/inventory/warehouses/WH-OFF"}]
    denied = suggestions.build_suggestion(_nobody(), block, "")
    assert denied["options"] == [] and denied["no_permission"]


# --- loop integration: propose hits a blocker → suggest → card streamed + pending persisted --------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_loop_turns_blocker_into_streamed_suggestion_with_pending(monkeypatch):
    from erp.assistant.models import Conversation
    from erp.assistant.services import agent

    user = _admin("sug_loop")
    conv = Conversation.objects.create(user=user)
    decisions = iter([
        {"action": "propose", "name": "create_sales_order_draft", "why": "Drafting order",
         "customer": "ABC Trading", "items": [{"item": "X", "quantity": "1"}]},
        {"action": "suggest", "resume": "I'll prepare the sales order for ABC Trading."},
    ])
    monkeypatch.setattr(agent, "complete_json", lambda *a, **k: next(decisions))
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["On it."]))

    events = list(agent.run(actor=user, conversation=conv, question="order for ABC Trading"))

    sug = next(e for e in events if e["type"] == "suggestion")
    assert sug["suggestion"]["status"] == "open"
    assert sug["suggestion"]["issue"]["entity"] == "customer"
    assert [o["kind"] for o in sug["suggestion"]["options"]] == ["inline_action", "deep_link"]

    # The blocked decision + resume ride the message meta for session 13's return detection.
    msg = conv.messages.get(role="assistant")
    assert msg.meta["suggestion"]["resume"] == "I'll prepare the sales order for ABC Trading."
    assert msg.meta["pending"]["name"] == "create_sales_order_draft"
    assert msg.meta["pending"]["customer"] == "ABC Trading"


# --- route guard: registry promises must exist in App.tsx ------------------------------------------

# Copied verbatim from apps/web/src/App.tsx. If this test fails, a route moved — update BOTH the
# registry in suggestions.py and this list to the new App.tsx truth (never guess from memory).
APP_ROUTES = [
    "/sales/customers",
    "/sales/customers/:code",
    "/purchasing/suppliers",
    "/purchasing/suppliers/:code",
    "/inventory/items",
    "/inventory/items/:sku",
    "/inventory/warehouses",
    "/inventory/warehouses/:code",
]


def test_registry_routes_all_exist_in_app_routes():
    static = {r for r in APP_ROUTES if ":" not in r}
    dynamic_prefixes = tuple(r.split(":")[0] for r in APP_ROUTES if ":" in r)
    for entity, reg in suggestions.ENTITY_REGISTRY.items():
        assert reg["create_route"] in static, f"{entity}: create_route not a real App.tsx route"
        assert reg["list_route"] in static, f"{entity}: list_route not a real App.tsx route"
        detail = reg["detail_route"].format(key="X")
        assert detail.startswith(dynamic_prefixes), f"{entity}: detail_route not a real App.tsx route"
