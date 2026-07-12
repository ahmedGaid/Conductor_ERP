"""L0 action graph (os-foundations FILE_01) — read API + registration decorator.

``unmet_requires`` is pinned against an empty and a seeded database; the decorator is pinned to
register a valid toy action and to reject an invalid one at declaration time (same import-time
rules as the built-in registry). Toy registrations are removed again — ``ACTIONS`` is module-global.
"""
from __future__ import annotations

import pytest

from erp.assistant.services import action_graph, actions
from erp.identity.models import User
from erp.inventory.domain.models import Item, Warehouse
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _admin(username: str = "graph_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


@pytest.fixture
def _clean_registry():
    before = set(actions.ACTIONS)
    yield
    for name in set(actions.ACTIONS) - before:
        del actions.ACTIONS[name]


def test_get_and_all_actions():
    assert action_graph.get("create_sales_order_draft").name == "create_sales_order_draft"
    assert len(action_graph.all_actions()) == len(actions.ACTIONS)
    with pytest.raises(KeyError):
        action_graph.get("no_such_action")


def test_unmet_requires_on_empty_db_names_the_missing_kinds():
    admin = _admin()
    assert action_graph.unmet_requires(admin, "create_sales_order_draft") == [
        "customer", "item", "warehouse"]
    assert action_graph.unmet_requires(admin, "create_journal_entry_draft") == ["account"]
    # No requires declared -> nothing unmet, even on an empty database.
    assert action_graph.unmet_requires(admin, "create_customer") == []


def test_unmet_requires_clears_as_records_appear():
    admin = _admin()
    Customer.objects.create(code="C-1", name="Nile Traders")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    assert action_graph.unmet_requires(admin, "create_sales_order_draft") == ["warehouse"]
    Warehouse.objects.create(code="WH-1", name="Main")
    assert action_graph.unmet_requires(admin, "create_sales_order_draft") == []


def test_unknown_kind_is_reported_not_raised(_clean_registry):
    @action_graph.register_action(name="toy_graph_action", description="test only", args={},
                                  requires=("unicorn",))
    def _pair():
        return (lambda actor, **_: {}), (lambda actor, payload: {})

    admin = _admin()
    assert action_graph.unmet_requires(admin, "toy_graph_action") == ["unicorn (unknown)"]


def test_decorator_registers_a_valid_action(_clean_registry):
    @action_graph.register_action(
        name="toy_registered_action", description="test only", args={"query": "a name"},
        effects=(actions.Effect("customer", "create"),), risk="draft", idempotency=("query",))
    def _pair():
        return (lambda actor, **_: {}), (lambda actor, payload: {})

    registered = action_graph.get("toy_registered_action")
    assert registered.effects[0].entity == "customer"
    assert registered.requires_confirm is True


def test_decorator_rejects_an_invalid_action(_clean_registry):
    with pytest.raises(AssertionError):
        @action_graph.register_action(name="toy_bad_action", description="test only", args={},
                                      risk="destructive", requires_confirm=False)
        def _pair():
            return (lambda actor, **_: {}), (lambda actor, payload: {})

    assert "toy_bad_action" not in actions.ACTIONS
